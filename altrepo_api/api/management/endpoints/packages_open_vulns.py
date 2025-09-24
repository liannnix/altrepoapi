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

import datetime

from typing import Union, Any, NamedTuple

from altrepo_api.api.base import APIWorker
from altrepo_api.libs.oval.altlinux_errata import (
    CVE_ID_TYPE,
    CVE_ID_PREFIX,
    BDU_ID_PREFIX,
)
from altrepo_api.libs.pagination import Paginator
from altrepo_api.libs.sorting import rich_sort
from altrepo_api.utils import make_tmp_table_name, sort_branches

from ..sql import sql


class PackagesOpenVulnsArgs(NamedTuple):
    input: Union[str, None]
    branch: Union[str, None]
    maintainer_nickname: Union[str, None]
    by_acl: str
    severity: Union[str, None]
    is_images: bool
    img: str
    limit: Union[int, None]
    page: Union[int, None]
    sort: Union[list[str], None]


class VulnInfoMeta(NamedTuple):
    id: str
    type: str = ""
    severity: str = ""
    refs_link: list[str] = []
    refs_type: list[str] = []


class PackageImagesMeta(NamedTuple):
    tag: str
    file: str
    show: str


class PackageMeta(NamedTuple):
    pkghash: int
    pkg_name: str
    pkg_version: str
    pkg_release: str
    modified: datetime.datetime
    branch: str
    vulns: list[VulnInfoMeta]
    images: list[PackageImagesMeta] = []

    def asdict(self) -> dict[str, Any]:
        return {
            "pkghash": self.pkghash,
            "pkg_name": self.pkg_name,
            "pkg_version": self.pkg_version,
            "pkg_release": self.pkg_release,
            "modified": self.modified,
            "branch": self.branch,
            "vulns": [el._asdict() for el in self.vulns],
            "images": sorted(
                [el._asdict() for el in self.images], key=lambda k: k["file"]
            ),
        }


class PackageBranchPair(NamedTuple):
    pkg_name: str
    branch: str


class PackagesOpenVulns(APIWorker):
    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = PackagesOpenVulnsArgs(**kwargs)
        self.sql = sql
        self.status: bool = False
        self.package_vulns: dict[PackageBranchPair, PackageMeta] = {}
        self.all_images: list[dict[str, str]] = []
        super().__init__()

    @property
    def _supported_branches(self) -> str:
        """
        Return SQL query to get supported branches.
        """
        branch_clause = (
            f"AND pkgset_name = '{self.args.branch}'" if self.args.branch else ""
        )
        return self.sql.supported_branches.format(branch=branch_clause)

    @property
    def _where_condition(self) -> str:
        """
        Search conditions for open vulnerabilities.
        """
        where_conditions = (
            f" AND pkg_name ILIKE '%{self.args.input}%'"
            if self.args.input
            and not self.args.input.startswith("CVE-")
            and not self.args.input.startswith("BDU:")
            else ""
        )
        return where_conditions

    def _maintainer_request_line(self, tmp_table: str) -> str:
        """
        Return SQL query for search for maintainer packages based on the filter.
        """
        request_line = ""
        if self.args.by_acl == "by_nick":
            request_line = self.sql.tmp_maintainer_pkg_by_nick_acl.format(
                tmp_table=tmp_table,
                columns=(
                    "(pkg_hash UInt64, pkgset_name String, "
                    "pkg_version String, pkg_release String)"
                ),
                maintainer_nickname=self.args.maintainer_nickname,
                branches=self._supported_branches,
            )
        if self.args.by_acl == "by_nick_leader":
            request_line = self.sql.tmp_maintainer_pkg_by_nick_leader_acl.format(
                tmp_table=tmp_table,
                columns=(
                    "(pkg_hash UInt64, pkgset_name String, "
                    "pkg_version String, pkg_release String)"
                ),
                maintainer_nickname=self.args.maintainer_nickname,
                branches=self._supported_branches,
            )
        if self.args.by_acl == "by_nick_or_group":
            request_line = self.sql.tmp_maintainer_pkg_by_nick_or_group_acl.format(
                tmp_table=tmp_table,
                columns=(
                    "(pkg_hash UInt64, pkgset_name String, "
                    "pkg_version String, pkg_release String)"
                ),
                maintainer_nickname=self.args.maintainer_nickname,
                branches=self._supported_branches,
            )
        if self.args.by_acl == "by_nick_leader_and_group":
            request_line = (
                self.sql.tmp_maintainer_pkg_by_nick_leader_and_group_acl.format(
                    tmp_table=tmp_table,
                    columns=(
                        "(pkg_hash UInt64, pkgset_name String, "
                        "pkg_version String, pkg_release String)"
                    ),
                    maintainer_nickname=self.args.maintainer_nickname,
                    branches=self._supported_branches,
                )
            )
        if self.args.by_acl == "by_packager":
            request_line = self.sql.tmp_maintainer_pkg.format(
                tmp_table=tmp_table,
                columns=(
                    "(pkg_hash UInt64, pkgset_name String, "
                    "pkg_version String, pkg_release String)"
                ),
                maintainer_nickname=self.args.maintainer_nickname,
                branches=self._supported_branches,
            )
        return request_line

    def _get_open_vulns(self) -> None:
        """
        Get all packages with open vulnerabilities.
        """
        self.status = False
        severity_clause = (
            f" AND vuln_severity = '{self.args.severity}'" if self.args.severity else ""
        )

        maintainer_clause = ""
        if self.args.maintainer_nickname and self.args.by_acl:
            tmp_table = make_tmp_table_name("maintainer_pkgs")
            _ = self.send_sql_request(self._maintainer_request_line(tmp_table))
            if not self.sql_status:
                return None
            maintainer_clause = (
                f"WHERE PKG.pkg_hash IN (SELECT pkg_hash FROM {tmp_table})"
            )

        response = self.send_sql_request(
            self.sql.get_all_open_vulns.format(
                branches=self._supported_branches,
                where_clause=self._where_condition,
                severity=severity_clause,
                maintainer_clause=maintainer_clause,
            )
        )
        if not response:
            _ = self.store_error(
                {
                    "message": "No packages found with open vulnerabilities",
                    "args": self.args._asdict(),
                }
            )
            return None
        if not self.sql_status:
            return None
        self.package_vulns = {
            PackageBranchPair(el[1], el[-2]): PackageMeta(
                *el[:-1], vulns=[VulnInfoMeta(*vuln) for vuln in el[-1]]
            )
            for el in response
        }
        self.status = True

    def _get_related_vulns(self) -> None:
        """
        Get related vulnerability id's by CVE and append to the vulnerabilities list.
        """
        self.status = False
        vulns: dict[str, list[VulnInfoMeta]] = {
            vul.id: [vul] for el in self.package_vulns.values() for vul in el.vulns
        }

        tmp_table = make_tmp_table_name("vulns")
        response = self.send_sql_request(
            self.sql.get_related_vulns_by_cves.format(tmp_table=tmp_table),
            external_tables=[
                {
                    "name": tmp_table,
                    "structure": [
                        ("vuln_id", "String"),
                    ],
                    "data": [{"vuln_id": el} for el in vulns.keys()],
                }
            ],
        )
        if not self.sql_status:
            return None

        for vuln in response:
            vuln = VulnInfoMeta(
                id=vuln[0],
                type=vuln[1],
                severity=vuln[4],
                refs_link=vuln[-2],
                refs_type=vuln[-1],
            )
            for ref_type, ref_link in zip(vuln.refs_type, vuln.refs_link):
                if ref_type == CVE_ID_TYPE and ref_link in vulns:
                    vulns[ref_link].append(vuln)

        copy_vulns = self.package_vulns.copy()
        for key, pkg in self.package_vulns.items():
            pkg_vulns = []
            for vuln in pkg.vulns:
                if vuln.id in vulns:
                    new_vulns = [
                        new_vuln
                        for new_vuln in vulns[vuln.id]
                        if new_vuln not in pkg_vulns
                    ]
                    pkg_vulns += new_vulns
            copy_vulns[key] = pkg._replace(vulns=pkg_vulns)

            # filter packages if a vulnerability number is specified in the search input
            if self.args.input and (
                self.args.input.startswith(CVE_ID_PREFIX)
                or self.args.input.startswith(BDU_ID_PREFIX)
            ):
                if not [
                    el.id for el in copy_vulns[key].vulns if self.args.input in el.id
                ]:
                    del copy_vulns[key]
        self.package_vulns = copy_vulns

        self.status = True

    def _get_pkg_images(self) -> None:
        """
        Get a list of images with the max version based on package hashes.
        """
        self.status = False
        tmp_table = "pkgs_hashes"
        response = self.send_sql_request(
            self.sql.get_pkg_images.format(tmp_table=tmp_table),
            external_tables=[
                {
                    "name": tmp_table,
                    "structure": [
                        ("pkg_hash", "UInt64"),
                    ],
                    "data": [
                        {"pkg_hash": el.pkghash} for el in self.package_vulns.values()
                    ],
                }
            ],
        )
        if not self.sql_status:
            return None
        if response:
            for el in response:
                key = PackageBranchPair(pkg_name=el[1], branch=el[2])
                if (
                    key in self.package_vulns
                    and self.package_vulns[key].pkghash == el[0]
                ):
                    self.package_vulns[key] = self.package_vulns[key]._replace(
                        images=[PackageImagesMeta(*img) for img in el[-1]]
                    )
                    for img in self.package_vulns[key].images:
                        if img._asdict() not in self.all_images:
                            self.all_images.append(img._asdict())
            self.all_images = sorted(self.all_images, key=lambda k: k["file"])
        self.status = True

    def get(self):
        self._get_open_vulns()
        if not self.status:
            return self.error

        # get related vulns for CVE
        self._get_related_vulns()
        if not self.status:
            return self.error

        # get a list of images
        self._get_pkg_images()
        if not self.status:
            return self.error

        if self.args.img:
            packages = [
                el.asdict()
                for el in self.package_vulns.values()
                if el.vulns != []
                and any(self.args.img == img.file for img in el.images)
            ]
        elif self.args.is_images:
            packages = [
                el.asdict()
                for el in self.package_vulns.values()
                if el.vulns != [] and el.images != []
            ]
        else:
            packages = [
                el.asdict() for el in self.package_vulns.values() if el.vulns != []
            ]
        if not packages:
            return self.store_error(
                {
                    "message": "No packages with open vulnerabilities found",
                    "args": self.args._asdict(),
                }
            )
        if self.args.sort:
            packages = rich_sort(packages, self.args.sort)

        paginator = Paginator(packages, self.args.limit)
        page_obj = paginator.get_page(self.args.page)

        res: dict[str, Any] = {
            "request_args": self.args._asdict(),
            "length": len(page_obj),
            "packages": page_obj,
            "images": self.all_images,
        }

        return (
            res,
            200,
            {
                "Access-Control-Expose-Headers": "X-Total-Count",
                "X-Total-Count": int(paginator.count),
            },
        )


class PackagesSupportedBranches(APIWorker):
    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.sql = sql
        super().__init__()

    def get(self):
        response = self.send_sql_request(self.sql.supported_branches.format(branch=""))
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error({"message": "No supported branches found"})
        res = {"branches": sort_branches([el[0] for el in response])}
        res["length"] = len(res["branches"])  # type: ignore
        return res, 200


class PackagesMaintainerList(APIWorker):
    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def get(self):
        branch_clause = (
            f"AND pkgset_name = '{self.args['branch']}'" if self.args["branch"] else ""
        )
        response = self.send_sql_request(
            self.sql.get_all_maintainers.format(branch=branch_clause)
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {"message": "No data not found in database", "args": self.args},
            )
        maintainers = [{"name": el[0], "nickname": el[1]} for el in response]

        paginator = Paginator(maintainers, self.args["limit"])
        page_obj = paginator.get_page(self.args["page"])

        res: dict[str, Any] = {
            "request_args": self.args,
            "length": len(page_obj),
            "maintainers": page_obj,
        }
        return (
            res,
            200,
            {
                "Access-Control-Expose-Headers": "X-Total-Count",
                "X-Total-Count": int(paginator.count),
            },
        )
