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

from datetime import datetime
from typing import Any, Iterable, NamedTuple, Union

from altrepo_api.api.base import APIWorker, WorkerResult
from altrepo_api.api.metadata import (
    KnownFilterTypes,
    MetadataAutocompleteItem,
    MetadataChoiceItem,
    MetadataItem,
)
from altrepo_api.libs.errata_server import rusty as rs
from altrepo_api.utils import sort_branches

from .common.constants import BDU_ID_TYPE, GHSA_ID_TYPE
from .vuln_list import is_any_vuln_id
from ..sql import sql
from ..parsers import pkgs_open_vulns_args


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
    type: str
    severity: str


class PackageImagesMeta(NamedTuple):
    tag: str
    file: str
    show: str


class PackageMeta(NamedTuple):
    pkg_hash: int
    pkg_name: str
    pkg_version: str
    pkg_release: str
    modified_date: datetime
    pkgset_name: str
    vulns: list[VulnInfoMeta]
    images: list[PackageImagesMeta]

    def asdict(self) -> dict[str, Any]:
        return {
            "pkghash": self.pkg_hash,
            "pkg_name": self.pkg_name,
            "pkg_version": self.pkg_version,
            "pkg_release": self.pkg_release,
            "modified": self.modified_date,
            "branch": self.pkgset_name,
            "vulns": [vuln._asdict() for vuln in self.vulns],
            "images": [
                img._asdict() for img in sorted(self.images, key=lambda k: k.file)
            ],
        }


class PackageBranchPair(NamedTuple):
    pkg_name: str
    branch: str


class PackagesOpenVulns(APIWorker):
    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.kwargs = kwargs
        self.args: PackagesOpenVulnsArgs
        self.sql = sql
        super().__init__()

    def check_params(self) -> bool:
        self.args = PackagesOpenVulnsArgs(**self.kwargs)

        self.logger.debug("args: %s", self.args)

        return True

    def _select_pkg_hash(self, branches: Iterable[str]) -> str:
        request_line: Union[str, None] = None

        if self.args.by_acl == "by_nick":
            request_line = self.sql.select_pkg_hash_by_nick_acl
        if self.args.by_acl == "by_nick_leader":
            request_line = self.sql.select_pkg_hash_by_nick_leader_acl
        if self.args.by_acl == "by_nick_or_group":
            request_line = self.sql.select_pkg_hash_by_nick_or_group_acl
        if self.args.by_acl == "by_nick_leader_and_group":
            request_line = self.sql.select_pkg_hash_by_nick_leader_and_group_acl
        if self.args.by_acl == "by_packager":
            request_line = self.sql.select_pkg_hash_by_packager

        return (
            request_line.format(
                maintainer_nickname=self.args.maintainer_nickname,
                branches=branches,
            )
            if request_line is not None
            else ""
        )

    @rs.resultify_method
    def _get_supported_branches(self) -> tuple[str, ...]:
        branch_condition = (
            f"AND pkgset_name = '{self.args.branch}'" if self.args.branch else ""
        )
        response = self.send_sql_request(
            self.sql.supported_branches.format(branch=branch_condition)
        )
        if not self.sql_status:
            raise Exception(self.error)
        if not response:
            self.store_error({"message": "Requested branch is not supported"})
            raise Exception(self.error)

        return tuple(branch for (branch,) in response)

    @rs.resultify_method
    def _get_open_vulns(self) -> tuple[dict[PackageBranchPair, PackageMeta], int]:
        branches = self._get_supported_branches().unwrap()

        severity_where_clause = (
            f"WHERE vuln_severity = '{self.args.severity}'"
            if self.args.severity
            else ""
        )

        where_clause = f"WHERE pkgset_name IN {branches}"

        if self.args.maintainer_nickname and self.args.by_acl:
            where_clause += (
                f" AND pkg_hash IN ({self._select_pkg_hash(branches=branches)})"
            )

        if self.args.input and not is_any_vuln_id(self.args.input):
            where_clause += f" AND pkg_name ILIKE '%{self.args.input}%'"

        final_where_clause = ""
        if self.args.input and is_any_vuln_id(self.args.input):
            final_where_clause = (
                f"WHERE arrayExists(v -> v.1 = '{self.args.input}', vulns)"
            )

        order_by_clause = "ORDER BY " + ", ".join(
            "{field} {direction}".format(
                field=field_name,
                direction="DESC" if sort_field.startswith("-") else "ASC",
            )
            for sort_field in self.args.sort or ["modified_date"]
            if (field_name := sort_field.removeprefix("-")) in PackageMeta._fields
        )

        limit_clause = f"LIMIT {self.args.limit}" if self.args.limit else ""

        offset_clause = (
            f"OFFSET {(self.args.page - 1) * self.args.limit}"
            if self.args.page and self.args.limit
            else ""
        )

        response = self.send_sql_request(
            self.sql.get_all_open_vulns.format(
                where_clause=where_clause,
                vuln_types=(BDU_ID_TYPE, GHSA_ID_TYPE),
                severity_where_clause=severity_where_clause,
                branches=branches,
                final_where_clause=final_where_clause,
                order_by_clause=order_by_clause,
                limit_clause=limit_clause,
                offset_clause=offset_clause,
            )
        )
        if not self.sql_status:
            raise Exception(self.error)
        if not response:
            self.store_error({"message": "No packages with open vulnerabilities found"})
            raise Exception(self.error)

        packge_vulns = {
            PackageBranchPair(pkg_name, pkgset_name): PackageMeta(
                pkg_hash=pkg_hash,
                pkg_name=pkg_name,
                pkg_version=pkg_version,
                pkg_release=pkg_release,
                modified_date=modified_date,
                pkgset_name=pkgset_name,
                vulns=[
                    VulnInfoMeta(id=vuln_id, type=vuln_type, severity=vuln_severity)
                    for vuln_id, vuln_type, vuln_severity in vulns
                ],
                images=[],
            )
            for (
                pkg_hash,
                pkg_name,
                pkg_version,
                pkg_release,
                modified_date,
                pkgset_name,
                vulns,
                _,
            ) in response
        }

        return packge_vulns, response[0][-1]

    @rs.resultify_method
    def _include_packages_images(
        self,
        package_vulns: dict[PackageBranchPair, PackageMeta],
    ) -> list[PackageImagesMeta]:
        tmp_table = "pkgs_hashes"
        response = self.send_sql_request(
            self.sql.get_pkg_images.format(tmp_table=tmp_table),
            external_tables=[
                {
                    "name": tmp_table,
                    "structure": [("pkg_hash", "UInt64")],
                    "data": [
                        {"pkg_hash": pkg.pkg_hash} for pkg in package_vulns.values()
                    ],
                }
            ],
        )
        if not self.sql_status:
            raise Exception(self.error)

        all_images: set[PackageImagesMeta] = set()

        if response:
            for pkg_srcrpm_hash, pkg_name, branch, tags in response:
                key = PackageBranchPair(pkg_name=pkg_name, branch=branch)
                if (
                    key in package_vulns
                    and package_vulns[key].pkg_hash == pkg_srcrpm_hash
                ):
                    package_vulns[key].images.extend(
                        PackageImagesMeta(
                            tag=tag,
                            file=file,
                            show=show,
                        )
                        for tag, file, show in tags
                    )
                    all_images.update(package_vulns[key].images)

        return sorted(all_images, key=lambda k: k.file)

    def get(self):
        if (result := self._get_open_vulns()).is_err():
            return self.error

        package_vulns, total_count = result.unwrap()

        # include a list of images
        if (result := self._include_packages_images(package_vulns)).is_err():
            return self.error

        all_images = result.unwrap()

        if self.args.img:
            packages = [
                pkg.asdict()
                for pkg in package_vulns.values()
                if pkg.vulns != []
                and any(self.args.img == img.file for img in pkg.images)
            ]
        elif self.args.is_images:
            packages = [
                pkg.asdict()
                for pkg in package_vulns.values()
                if pkg.vulns != [] and pkg.images != []
            ]
        else:
            packages = [
                pkg.asdict() for pkg in package_vulns.values() if pkg.vulns != []
            ]

        if not packages:
            return self.store_error(
                {"message": "No packages with open vulnerabilities found"}
            )

        return (
            {
                "request_args": self.args._asdict(),
                "length": total_count,
                "packages": packages,
                "images": [img._asdict() for img in all_images],
            },
            200,
            {
                "Access-Control-Expose-Headers": "X-Total-Count",
                "X-Total-Count": total_count,
            },
        )

    def metadata(self) -> WorkerResult:
        metadata = []
        for arg in pkgs_open_vulns_args.args:
            item_info = {
                "name": arg.name,
                "label": arg.name.replace("_", " ").capitalize(),
                "help_text": arg.help,
            }

            if arg.name in ("by_acl", "severity"):
                metadata.append(
                    MetadataItem(
                        **item_info,
                        type=KnownFilterTypes.CHOICE,
                        choices=[
                            MetadataChoiceItem(
                                value=choice,
                                display_name=choice.replace("_", " ").capitalize(),
                            )
                            for choice in arg.choices
                        ],
                    )
                )

            if arg.name == "maintainer_nickname":
                metadata.append(
                    MetadataItem(
                        **item_info,
                        type=KnownFilterTypes.AUTOCOMPLETE,
                        autocomplete=MetadataAutocompleteItem(
                            endpoint="/packages/maintainer_list",
                            data_path="$.maintainers[*].nickname",
                            search_param="maintainer_nickname",
                            pagination=False,
                        ),
                    )
                )

            if arg.name == "branch":
                metadata.append(
                    MetadataItem(
                        **item_info,
                        type=KnownFilterTypes.AUTOCOMPLETE,
                        autocomplete=MetadataAutocompleteItem(
                            endpoint="/packages/supported_branches",
                            data_path="$.branches[*]",
                            pagination=False,
                        ),
                    )
                )

            if arg.name == "img":
                metadata.append(
                    MetadataItem(
                        **item_info,
                        type=KnownFilterTypes.AUTOCOMPLETE,
                        autocomplete=MetadataAutocompleteItem(
                            endpoint="/packages/image_list",
                            search_param="img",
                            data_path="$.images[*]",
                            pagination=True,
                        ),
                    )
                )

        return {
            "length": len(metadata),
            "metadata": [el.asdict() for el in metadata],
        }, 200


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


class PackagesMaintainerListArgs(NamedTuple):
    branch: str | None
    maintainer_nickname: str | None
    limit: int | None
    page: int | None


class PackagesMaintainerList(APIWorker):
    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.kwargs = kwargs
        self.sql = sql
        self.args: PackagesMaintainerListArgs
        super().__init__()

    def check_params(self) -> bool:
        self.args = PackagesMaintainerListArgs(**self.kwargs)
        self.logger.info("GET args: %s", self.args)
        return True

    @property
    def _branch_clause(self):
        if self.args.branch:
            return f"AND pkgset_name = '{self.args.branch}'"
        return ""

    @property
    def _nickname_clause(self):
        if self.args.maintainer_nickname:
            return f"AND packager_nick ILIKE '%{self.args.maintainer_nickname}%'"
        return ""

    @property
    def _limit(self):
        if self.args.limit:
            return f"LIMIT {self.args.limit}"
        return ""

    @property
    def _page(self):
        if self.args.limit and self.args.page:
            page = self.args.page
            per_page = self.args.limit
            offset = (page - 1) * per_page
            return f"OFFSET {offset}"
        return ""

    def get(self):
        response = self.send_sql_request(
            self.sql.get_all_maintainers.format(
                branch=self._branch_clause,
                nickname=self._nickname_clause,
                limit=self._limit,
                page=self._page,
            )
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {"message": "No data not found in database", "args": self.args},
            )
        maintainers = [{"name": el[0], "nickname": el[1]} for el in response]

        return (
            {
                "request_args": self.args._asdict(),
                "maintainers": maintainers,
            },
            200,
            {
                "Access-Control-Expose-Headers": "X-Total-Count",
                "X-Total-Count": response[0][-1],
            },
        )


class PackagesImageListArgs(NamedTuple):
    img: str | None
    limit: int | None
    page: int | None


class PackagesImageList(APIWorker):
    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.kwargs = kwargs
        self.sql = sql
        self.args: PackagesImageListArgs
        super().__init__()

    def check_params(self) -> bool:
        self.args = PackagesImageListArgs(**self.kwargs)
        self.logger.info("GET args: %s", self.args)
        return True

    @property
    def _where_clause(self):
        if self.args.img:
            return f"WHERE img_file ILIKE '%{self.args.img}%'"
        return ""

    @property
    def _limit_clause(self):
        if self.args.limit:
            return f"LIMIT {self.args.limit}"
        return ""

    @property
    def _page_clause(self):
        if self.args.limit and self.args.page:
            page = self.args.page
            per_page = self.args.limit
            offset = (page - 1) * per_page
            return f"OFFSET {offset}"
        return ""

    def get(self):
        response = self.send_sql_request(
            self.sql.get_img_files_list.format(
                where_clause=self._where_clause,
                limit_clause=self._limit_clause,
                page_clause=self._page_clause,
            )
        )

        if not self.sql_status:
            return self.error

        if not response:
            return self.store_error({"message": "No images found"})

        return (
            {
                "request_args": self.args._asdict(),
                "images": [img_file for (img_file, _) in response],
            },
            200,
            {
                "Access-Control-Expose-Headers": "X-Total-Count",
                "X-Total-Count": response[0][-1],
            },
        )
