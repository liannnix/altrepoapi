# ALTRepo API
# Copyright (C) 2021-2023  BaseALT Ltd

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import zipfile
from io import BytesIO

from altrepo_api.utils import make_tmp_table_name
from altrepo_api.api.base import APIWorker
from altrepo_api.api.misc import lut
from ..sql import sql

from .xml_builder import (
    OVALBuilder,
    BugzillaInfo,
    ErrataHistoryRecord,
    PackageInfo,
    VulnerabilityInfo,
)


ZIP_FILE_NAME = "oval_definitions_{}.zip"


class OvalExport(APIWorker):
    """Retrieves OVAL definitions of closed issues of branch packages from database."""

    def __init__(self, connection, branch, **kwargs):
        self.branch = branch
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        self.validation_results = []

        if self.branch not in lut.oval_export_branches:
            self.validation_results.append(f"unknown package set name : {self.branch}")
            self.validation_results.append(
                f"allowed package set names are : {lut.oval_export_branches}"
            )

        if self.validation_results != []:
            return False

        return True

    def get(self):
        package_name = self.args["package_name"]
        one_file = self.args["one_file"]
        print(f"DBG: {one_file}")
        pkg_name_clause = ""

        if package_name:
            pkg_name_clause = f"AND pkg_name = '{package_name}'"
            zip_file_name = ZIP_FILE_NAME.format(self.branch + "_" + package_name)
        else:
            zip_file_name = ZIP_FILE_NAME.format(self.branch)

        # get ErrataHistory
        response = self.send_sql_request(
            self.sql.get_errata_history_by_branch_tasks.format(
                branch=self.branch, pkg_name_clause=pkg_name_clause
            )
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {
                    "message": "No data found in DB",
                    "args": self.args,
                }
            )
        # FIXME: handle duplicated errata records for tasks state transitions from TESTED|EPERM to DONE
        erratas = [ErrataHistoryRecord(*el) for el in response]
        # collect bugzilla and vulnerability ids from errata
        bz_ids: list[int] = []
        vuln_ids: list[str] = []
        for err in erratas:
            for type_, link in zip(err.eh_references_type, err.eh_references_link):
                if type_ == "bug":
                    bz_ids.append(int(link))
                elif type_ == "vuln":
                    vuln_ids.append(link)

        # get binary packages info by source packages hashes
        tmp_table = make_tmp_table_name("src_hashes")
        response = self.send_sql_request(
            self.sql.get_bin_pkgs_by_src_hshs.format(tmp_table=tmp_table),
            external_tables=[
                {
                    "name": tmp_table,
                    "structure": [("pkg_hash", "UInt64")],
                    "data": [{"pkg_hash": e.pkg_hash} for e in erratas],
                },
            ],
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error({"message": "No package information found in DB"})

        binaries: dict[int, list[PackageInfo]] = {}
        for pkg in (PackageInfo(*el) for el in response):
            if pkg.srcrpm_hash not in binaries:
                binaries[pkg.srcrpm_hash] = []
            binaries[pkg.srcrpm_hash].append(pkg)

        # get bugz info by ids from errata
        bugz: dict[int, BugzillaInfo] = {}
        if bz_ids:
            tmp_table = make_tmp_table_name("bz_ids")
            response = self.send_sql_request(
                self.sql.get_bugzilla_summary_by_ids.format(tmp_table=tmp_table),
                external_tables=[
                    {
                        "name": tmp_table,
                        "structure": [("bz_id", "UInt32")],
                        "data": [{"bz_id": bz_id} for bz_id in bz_ids],
                    },
                ],
            )
            if not self.sql_status:
                return self.error
            if not response:
                return self.store_error({"message": "No bugzilla info found in DB"})

            bugz = {bz.id: bz for bz in (BugzillaInfo(*el) for el in response)}

        # get vulnerabilities info by ids form errata
        vulns: dict[str, VulnerabilityInfo] = {}
        bdus_by_cves: dict[str, VulnerabilityInfo] = {}
        if vuln_ids:
            # collect vulnerabilities by references from errata records
            tmp_table = make_tmp_table_name("vuln_ids")
            response = self.send_sql_request(
                self.sql.get_vulns_info_by_ids.format(tmp_table=tmp_table),
                external_tables=[
                    {
                        "name": tmp_table,
                        "structure": [("vuln_id", "String")],
                        "data": [{"vuln_id": vuln_id} for vuln_id in vuln_ids],
                    },
                ],
            )
            if not self.sql_status:
                return self.error
            if not response:
                return self.store_error(
                    {"message": "No vulnerabilities info found in DB"}
                )
            vulns = {
                vuln.id: vuln for vuln in (VulnerabilityInfo(*el) for el in response)
            }
            # collect BDUs by CVE id's references
            response = self.send_sql_request(
                self.sql.get_bdus_info_by_cve_ids.format(tmp_table=tmp_table),
                external_tables=[
                    {
                        "name": tmp_table,
                        "structure": [("vuln_id", "String")],
                        "data": [{"vuln_id": vuln_id} for vuln_id in vuln_ids],
                    },
                ],
            )
            if not self.sql_status:
                return self.error
            if not response:
                return self.store_error(
                    {"message": "No vulnerabilities info found in DB"}
                )
            bdus_by_cves = {
                vuln.id: vuln for vuln in (VulnerabilityInfo(*el) for el in response)
            }

        xml_bulder = OVALBuilder(erratas, binaries, bugz, vulns, bdus_by_cves)

        zip_buffer = BytesIO()
        with zipfile.ZipFile(
            file=zip_buffer,
            mode="a",
            compression=zipfile.ZIP_DEFLATED,
            allowZip64=False,
            compresslevel=5,
        ) as zip_file:
            for xml_file_name, xml_file in xml_bulder.build(one_file):
                zip_file.writestr(xml_file_name, xml_file.getvalue())
                xml_file.close()

        return {"file": zip_buffer, "file_name": zip_file_name}, 200


class OvalBranches(APIWorker):
    """Retrieves branches with OVAL definitions export available."""

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def get(self):
        branches = lut.oval_export_branches
        return {"length": len(branches), "branches": branches}, 200
