# ALTRepo API
# Copyright (C) 2021-2025  BaseALT Ltd

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

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any

from altrepo_api.api.base import APIWorker
from altrepo_api.api.misc import lut
from altrepo_api.api.parser import bug_id_type
from altrepo_api.utils import make_tmp_table_name

from .tools.base import Reference
from .tools.constants import (
    BDU_ID_TYPE,
    BUG_ID_TYPE,
    CVE_ID_TYPE,
    GHSA_ID_TYPE,
    MFSA_ID_TYPE,
    OVE_ID_TYPE,
    DT_NEVER,
)
from .tools.helpers.vuln import Bug
from .tools.utils import parse_vuln_id_list
from ..sql import sql


@dataclass
class VulnerabilityInfo:
    id: str
    type: str = ""
    summary: str = ""
    score: float = 0.0
    severity: str = ""
    url: str = ""
    modified_date: datetime = DT_NEVER
    published_date: datetime = DT_NEVER
    refs_link: list[str] = field(default_factory=list)
    refs_type: list[str] = field(default_factory=list)
    is_valid: bool = False
    related_vulns: list[str] = field(default_factory=list)

    def asdict(self) -> dict[str, Any]:
        res = asdict(self)

        del res["refs_type"]
        del res["refs_link"]
        res["modified_date"] = self.modified_date.isoformat()
        res["published_date"] = self.published_date.isoformat()
        res["references"] = [r for r in self.refs_link]

        return res


def bug2vulninfo(bug: Bug) -> VulnerabilityInfo:
    return VulnerabilityInfo(
        id=str(bug.id),
        type=str(BUG_ID_TYPE).upper(),
        summary=bug.summary,
        url=f"{lut.bugzilla_base}/{bug.id}",
        modified_date=bug.last_changed,
        published_date=bug.last_changed,
        is_valid=bug.is_valid,
    )


class VulnsInfo(APIWorker):
    """
    Find vulnerability information.
    """

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        self.vulns: set[Reference] = set()
        super().__init__()

    def check_params_post(self):
        try:
            self.vulns = set(parse_vuln_id_list(self.args["json_data"]["vuln_ids"]))
            # validate Bug ID is within safe range of DB representation
            _ = [
                bug_id_type(b)
                for b in (int(v.link) for v in self.vulns if v.type == BUG_ID_TYPE)
            ]
        except (AttributeError, KeyError, TypeError, ValueError) as e:
            self.validation_results.append(f"Payload data parsing error: {e}")
            return False

        return True

    def __get_vuln_ino_by_ids(
        self, vuln_ids: list[str], sql: str
    ) -> dict[str, VulnerabilityInfo]:
        vulns: dict[str, VulnerabilityInfo] = {}

        tmp_table = make_tmp_table_name("vuln_ids")
        response = self.send_sql_request(
            sql.format(tmp_table=tmp_table),
            external_tables=[
                {
                    "name": tmp_table,
                    "structure": [("vuln_id", "String")],
                    "data": [{"vuln_id": v_id} for v_id in vuln_ids],
                },
            ],
        )

        if not self.sql_status:
            raise RuntimeError("SQL request error")

        if response:
            vulns = {el[0]: VulnerabilityInfo(*el, is_valid=True) for el in response}

        return vulns

    def _collect_vuln_by_ids(self, vuln_ids: list[str]) -> dict[str, VulnerabilityInfo]:
        return self.__get_vuln_ino_by_ids(vuln_ids, self.sql.get_vuln_info_by_ids)

    def _collect_related_cve_by_ids(
        self, cve_ids: list[str]
    ) -> dict[str, VulnerabilityInfo]:
        return self.__get_vuln_ino_by_ids(cve_ids, self.sql.get_related_vulns_by_cves)

    def post(self):
        bugs: dict[int, Bug] = {}
        vulns_found: dict[str, VulnerabilityInfo] = {}

        bug_ids = [int(v.link) for v in self.vulns if v.type == BUG_ID_TYPE]
        bdu_ids = [v.link for v in self.vulns if v.type == BDU_ID_TYPE]
        cve_ids = [v.link for v in self.vulns if v.type == CVE_ID_TYPE]
        ghsa_ids = [v.link for v in self.vulns if v.type == GHSA_ID_TYPE]

        # get a list of found bugs in Bugzilla
        if bug_ids:
            tmp_table = make_tmp_table_name("bz_ids")
            response = self.send_sql_request(
                self.sql.get_bugs_by_ids.format(tmp_table=tmp_table),
                external_tables=[
                    {
                        "name": tmp_table,
                        "structure": [("bz_id", "UInt32")],
                        "data": [{"bz_id": bz_id} for bz_id in bug_ids],
                    },
                ],
            )
            if not self.sql_status:
                return self.error
            bugs = {row[0]: Bug(*row, is_valid=True) for row in response}

        def process_vulns(vuiln_ids: list[str]) -> dict[str, VulnerabilityInfo]:
            vulns_found: dict[str, VulnerabilityInfo] = dict()

            response = self._collect_vuln_by_ids(vuiln_ids)

            if response:
                cve_ids = list()
                for v in response.values():
                    for ref_type, ref_link in zip(v.refs_type, v.refs_link):
                        if ref_type == CVE_ID_TYPE:
                            cve_ids.append(ref_link)
                            v.related_vulns.append(ref_link)
                    vulns_found[v.id] = v

                # get related CVEs
                response = self._collect_vuln_by_ids(cve_ids)
                if response:
                    vulns_found = {**vulns_found, **response}

            return vulns_found

        try:
            if cve_ids:
                # get CVE info
                response = self._collect_vuln_by_ids(cve_ids)

                if response:
                    vulns_found = response

                    # get related vulnerability id's from CVE
                    response = self._collect_related_cve_by_ids(
                        list(vulns_found.keys())
                    )

                    for vuln in response.values():
                        for ref_type, ref_link in zip(vuln.refs_type, vuln.refs_link):
                            if ref_type == CVE_ID_TYPE and ref_link in vulns_found:
                                vulns_found[ref_link].related_vulns.append(vuln.id)
                        vulns_found[vuln.id] = vuln
                        # remove non CVE IDs from input if found as related through give CVE IDs
                        if vuln.id in bdu_ids.copy():
                            bdu_ids.remove(vuln.id)
                        if vuln.id in ghsa_ids.copy():
                            ghsa_ids.remove(vuln.id)

            if bdu_ids:
                # get BDU info
                vulns_found = {**vulns_found, **process_vulns(bdu_ids)}

            if ghsa_ids:
                # get GHSA info
                vulns_found = {**vulns_found, **process_vulns(ghsa_ids)}
        except RuntimeError:
            return self.error

        vulns = list(vulns_found.values())

        # add not found CVEs to the resulting list of vulnerabilities
        # FIXME: maybe put it into `not_found` IDs list?
        for cve in cve_ids:
            if cve not in vulns_found:
                vulns.insert(0, VulnerabilityInfo(id=cve, type=CVE_ID_TYPE))

        # convert found bugs info to vulnerability objects
        vulns.extend([bug2vulninfo(bug) for bug in bugs.values()])

        # add supported vulnerabilities that has no data in DB
        vulns.extend(
            VulnerabilityInfo(id=v.link, type=v.type)
            for v in self.vulns
            if v.type in (MFSA_ID_TYPE, OVE_ID_TYPE)
        )

        if not vulns:
            return self.store_error(
                {
                    "message": f"No data info found in DB for {[v.link for v in self.vulns]}"
                }
            )

        # BDU, GHSA and Bugzilla vulnerabilities not found in the DB
        not_found_vulns = [
            v_id for v_id in bdu_ids + ghsa_ids if v_id not in vulns_found.keys()
        ] + [str(bug) for bug in bug_ids if bug not in bugs.keys()]

        res = {
            "vulns": [v.asdict() for v in vulns],
            "not_found": not_found_vulns,
        }

        return res, 200
