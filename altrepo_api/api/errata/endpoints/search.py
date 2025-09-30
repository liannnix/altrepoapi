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

import re

from dataclasses import dataclass, field
from typing import NamedTuple, Any, Optional, Union

from altrepo_api.api.base import APIWorker, WorkerResult
from altrepo_api.api.metadata import KnownFilterTypes, MetadataChoiceItem, MetadataItem
from altrepo_api.api.misc import lut
from altrepo_api.libs.pagination import Paginator
from altrepo_api.libs.sorting import rich_sort
from altrepo_api.utils import make_tmp_table_name, sort_branches

from .common import ErrataID, get_erratas_by_search_conditions
from ..parsers import find_erratas_args
from ..sql import sql

_vuln_id_match = re.compile(r"(^CVE-\d{4}-\d{4,}$)|(^BDU:\d{4}-\d{5}$)|(^\d{4,}$)")


class ErrataInfo(NamedTuple):
    errata_id: str
    eh_type: str
    task_id: int
    branch: str
    pkgs: list[tuple[int, str, str, str]]
    vuln_ids: list[str]
    vuln_types: list[str]
    changed: str
    is_discarded: bool
    vulnerabilities: list[dict[str, str]] = []
    packages: list[dict[str, str]] = []


class Vulns(NamedTuple):
    id: str
    type: str


class PackageInfo(NamedTuple):
    pkghash: int
    pkg_name: str
    pkg_version: str
    pkg_release: str


class FindImagesArgs(NamedTuple):
    uuid: str
    branch: str
    component: Union[str, None]
    input: Union[list[str], None]
    type: Union[list[str], None]
    limit: Union[int, None]
    page: Union[int, None]
    is_discarded: bool
    sort: Union[list[str], None]


class ImageErratas(NamedTuple):
    img_pkg_hash: str
    summary: str
    pkg_name: str
    pkg_arch: str
    img_pkg_version: str
    img_pkg_release: str
    pkg_hash: str
    pkg_version: str
    pkg_release: str
    errata_id: str
    eh_type: str
    task_id: int
    branch: str
    changed: str
    is_discarded: bool
    vulnerabilities: list[dict[str, str]]


@dataclass
class ImageErrataInfo:
    errata_id: str
    eh_type: str
    task_id: int
    branch: str
    pkg_hash: int
    pkg_name: str
    pkg_version: str
    pkg_release: str
    vuln_ids: list[str]
    vuln_types: list[str]
    changed: str
    is_discarded: bool
    vulnerabilities: list[dict[str, str]] = field(default_factory=list)

    def __post_init__(self):
        for v, t in zip(self.vuln_ids, self.vuln_types):
            new_vulnerability = {"id": v, "type": t}
            if new_vulnerability not in self.vulnerabilities:
                self.vulnerabilities.append(new_vulnerability)


class Search(APIWorker):
    """Gather Errata data from DB by search conditions"""

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def check_params(self) -> bool:
        if not any(
            (
                self.args.get("name"),
                self.args.get("branch"),
                self.args.get("vuln_id"),
                self.args.get("errata_id"),
            )
        ):
            self.validation_results.append(
                "At least one of `branch`, `name`, `vuln_id` or `errata_id` argument should be specified"
            )

        # validate `vuln_id`
        vuln_id = self.args.get("vuln_id")
        if vuln_id and _vuln_id_match.match(vuln_id) is None:
            self.validation_results.append(f"Not a valid CVE, BDU or Bug id: {vuln_id}")

        if self.validation_results != []:
            return False

        return True

    def get(self):
        branch = self.args.get("branch")
        errata_id = self.args.get("errata_id")
        package_name = self.args.get("name")
        vuln_id = self.args.get("vuln_id")

        search_conditions = []

        if branch is not None:
            search_conditions.append(f"pkgset_name = '{branch}'")

        if errata_id is not None:
            search_conditions.append(
                f"arrayExists(x -> (x ILIKE '%{errata_id}%'), eh_references.link)"
            )

        if vuln_id is not None:
            search_conditions.append(
                f"arrayExists(x -> (x = '{vuln_id}'), eh_references.link)"
            )

        if package_name is not None:
            search_conditions.append(f"pkg_name LIKE '%{package_name}%'")

        where_clause = (
            self.sql.search_errata_where_clause
            + "AND "
            + " AND ".join(search_conditions)
        )

        erratas = get_erratas_by_search_conditions(self, where_clause)
        if not self.status or erratas is None:
            return self.error

        return {"erratas": [errata.asdict() for errata in erratas]}, 200


class ErrataIds(APIWorker):
    """Get list of valid errata ids"""

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def get(self):
        response = self.send_sql_request(self.sql.get_valid_errata_ids)
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error({"message": "No data found in DB"})

        errata_ids = [
            e.id
            for e in sorted((ErrataID.from_id(el[0]) for el in response), reverse=True)
        ]

        return {"errata_ids": errata_ids}, 200


class FindErratasArgs(NamedTuple):
    branch: Optional[str] = None
    type: Optional[str] = None
    input: Optional[list[str]] = None
    page: Optional[int] = None
    limit: Optional[int] = None
    state: Optional[str] = None


class FindErratas(APIWorker):
    """
    Erratas search lookup by id, vulnerability id or package name.
    """

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = FindErratasArgs(**kwargs)
        self.sql = sql
        super().__init__()

    @property
    def _branch_clause(self) -> str:
        return f"AND pkgset_name = '{self.args.branch}'" if self.args.branch else ""

    @property
    def _type_clauses(self) -> list[str]:
        conditions = []
        tp = self.args.type or ""
        eh_type = lut.known_errata_type.get(tp, "")

        conditions = [f"type IN {eh_type}"] if eh_type else []
        if tp in (lut.errata_ref_type_bug, lut.errata_ref_type_vuln):
            conditions.append(f"arrayExists(x -> x = '{tp}', refs_types)")

        return conditions

    @property
    def _state_clause(self) -> str:
        if self.args.state:
            return "discard = {}".format(self.args.state == "discarded")
        return ""

    @property
    def _input_clause(self) -> str:
        input_val: list[str] = self.args.input or []
        conditions = [
            " OR ".join(
                (
                    f"(errata_id ILIKE '%{v}%')",
                    f"arrayExists(x -> x.2 ILIKE '%{v}%', packages)",
                    f"arrayExists(x -> x ILIKE '%{v}%', refs_links)",
                )
            )
            for v in input_val
        ]
        if conditions:
            return "(" + " OR ".join(conditions) + ")"
        return ""

    @property
    def _where_conditions(self) -> str:
        conditions = []
        if self._type_clauses:
            conditions.extend(self._type_clauses)

        if self._state_clause:
            conditions.append(self._state_clause)

        if self._input_clause:
            conditions.append(self._input_clause)

        if conditions:
            return f"WHERE {' AND '.join(conditions)}"
        return ""

    def check_params(self) -> bool:
        if self.args.input and len(self.args.input) > 3:
            self.validation_results.append(
                "input values list should contain no more than 3 elements"
            )

        return self.validation_results == []

    def get(self):

        limit = self.args.limit
        page = self.args.page

        response = self.send_sql_request(
            self.sql.find_erratas.format(
                branch=self._branch_clause, where_clause=self._where_conditions
            )
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {"message": "No data not found in database"},
            )

        erratas = []
        for el in response:
            errata_info = ErrataInfo(*el)
            vulns = [
                Vulns(v_id, v_type)._asdict()
                for v_id, v_type in zip(errata_info.vuln_ids, errata_info.vuln_types)
            ]
            pkgs = [PackageInfo(*info)._asdict() for info in errata_info.pkgs]

            erratas.append(
                errata_info._replace(vulnerabilities=vulns, packages=pkgs)._asdict()
            )

        paginator = Paginator(erratas, limit)
        page_obj = paginator.get_page(page)

        return (
            {
                "request_args": self.args,
                "erratas": page_obj,
                "length": len(page_obj),
            },
            200,
            {
                "Access-Control-Expose-Headers": "X-Total-Count",
                "X-Total-Count": int(paginator.count),
            },
        )

    def metadata(self) -> WorkerResult:
        metadata = []
        for arg in find_erratas_args.args:
            item_info = {
                "name": arg.name,
                "label": arg.name.replace("_", " ").capitalize(),
                "help_text": arg.help,
            }

            if arg.name in ["type", "state"]:
                metadata.append(
                    MetadataItem(
                        **item_info,
                        type=KnownFilterTypes.CHOICE,
                        choices=[
                            MetadataChoiceItem(
                                value=choice, display_name=choice.capitalize()
                            )
                            for choice in arg.choices
                            if choice != "all"
                        ],
                    )
                )

            if arg.name == "branch":
                branches = self.send_sql_request(self.sql.get_errata_branches)
                if branches:
                    metadata.append(
                        MetadataItem(
                            **item_info,
                            type=KnownFilterTypes.CHOICE,
                            choices=[
                                MetadataChoiceItem(value=branch, display_name=branch)
                                for branch in sort_branches(
                                    branch for branch, in branches
                                )
                            ],
                        )
                    )
        return {
            "length": len(metadata),
            "metadata": [el.asdict() for el in metadata],
        }, 200


class FindImageErratas(APIWorker):
    """
    Erratas search lookup by image UUID.
    """

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = self._get_args(kwargs)
        self.sql = sql
        self.status: bool = False
        self.erratas: dict[int, ImageErrataInfo] = {}
        super().__init__()

    def check_params(self) -> bool:
        if self.args.input and len(self.args.input) > 3:
            self.validation_results.append(
                "input values list should contain no more than 3 elements"
            )

        if self.validation_results != []:
            return False
        return True

    @staticmethod
    def _get_args(args: dict[str, Any]) -> FindImagesArgs:
        """
        Unpack query arguments into Namedtuple.
        """
        res = FindImagesArgs(**args)
        res = res._replace(type=lut.known_errata_type.get(args["type"], None))
        return res

    def _get_where_condition(self) -> str:
        where_conditions: str = (
            f" AND type IN {self.args.type}" if self.args.type else ""
        )
        where_conditions += (
            f" AND discard = {self.args.is_discarded}" if self.args.is_discarded else ""
        )

        if self.args.input:
            conditions: list[str] = [
                " OR ".join(
                    (
                        f"(errata_id ILIKE '%{v}%')",
                        f"name ILIKE '%{v}%'",
                        f"bin_pkg_name ILIKE '%{v}%'",
                        f"arrayExists(x -> x ILIKE '%{v}%', refs_links)",
                    )
                )
                for v in self.args.input
            ]
            where_conditions += f" AND ({' OR '.join(conditions)})"
        return where_conditions

    def _tmp_image_pkg_hashes(self) -> Union[str, None]:
        """
        Record the package hashes included in the image in a temporary table.
        """
        self.status = False
        if self.args.component is not None:
            component_clause = f"AND pkgset_nodename = '{self.args.component}'"
        else:
            component_clause = ""

        tmp_table = make_tmp_table_name("pkg_img_hashes")

        _ = self.send_sql_request(
            self.sql.tmp_image_pkg_hashes.format(
                tmp_table=tmp_table,
                uuid=self.args.uuid,
                branch=self.args.branch,
                component=component_clause,
            ),
        )
        if not self.sql_status:
            return None
        self.status = True
        return tmp_table

    def _get_erratas(self, tmp_pkg_hashes: str) -> None:
        """
        Get Erratas list for image packages.
        """
        self.status = False
        response = self.send_sql_request(
            self.sql.find_imgs_erratas.format(
                branch=self.args.branch,
                tmp_table=tmp_pkg_hashes,
                where_clause=self._get_where_condition(),
            )
        )
        if not response:
            _ = self.store_error({"message": "No found erratas"})
            return None
        if not self.sql_status:
            return None
        self.status = True

        for el in response:
            pkg_hash, _, pkg_buildtime, src_hash = el[:4]
            errata = ImageErrataInfo(*el[4:])
            # filter erratas that has source package hashes greater that image binaries source
            # and errata created later than binary package build time
            if errata.pkg_hash > src_hash and pkg_buildtime <= errata.changed:
                self.erratas[pkg_hash] = errata

    def _get_errata_pkgs_info(self) -> Union[list[dict[str, Any]], None]:
        """
        Get information about image packages that have erratas available.
        """
        self.status = False
        tmp_table = make_tmp_table_name("errata_pkg_hashes")
        response = self.send_sql_request(
            self.sql.get_last_image_pkgs_info.format(
                tmp_table=tmp_table, branch=self.args.branch
            ),
            external_tables=[
                {
                    "name": tmp_table,
                    "structure": [
                        ("pkg_hash", "UInt64"),
                    ],
                    "data": [
                        {"pkg_hash": pkg_hash} for pkg_hash in self.erratas.keys()
                    ],
                }
            ],
        )
        if not response:
            _ = self.store_error({"message": "No found packages"})
            return None
        if not self.sql_status:
            return None
        self.status = True
        pkgs = []
        for el in response:
            pkg = ImageErratas(
                *el[:-2],
                errata_id=self.erratas[el[0]].errata_id,
                eh_type=self.erratas[el[0]].eh_type,
                task_id=self.erratas[el[0]].task_id,
                branch=self.erratas[el[0]].branch,
                changed=self.erratas[el[0]].changed,
                is_discarded=self.erratas[el[0]].is_discarded,
                vulnerabilities=self.erratas[el[0]].vulnerabilities,
            )
            pkgs.append(pkg._asdict())
        return pkgs

    def get(self):
        tmp_pkg_hashes = self._tmp_image_pkg_hashes()
        if not self.status or not tmp_pkg_hashes:
            return self.error

        self._get_erratas(tmp_pkg_hashes)
        if not self.status:
            return self.error

        packages = self._get_errata_pkgs_info()
        if not self.status or not packages:
            return self.error

        if self.args.sort:
            packages = rich_sort(packages, self.args.sort)

        paginator = Paginator(packages, self.args.limit)
        page_obj = paginator.get_page(self.args.page)

        res: dict[str, Any] = {
            "request_args": self.args._asdict(),
            "length": len(page_obj),
            "erratas": page_obj,
        }

        return (
            res,
            200,
            {
                "Access-Control-Expose-Headers": "X-Total-Count",
                "X-Total-Count": int(paginator.count),
            },
        )
