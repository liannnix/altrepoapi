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

import re

from typing import NamedTuple, Any

from altrepo_api.api.base import APIWorker
from altrepo_api.api.misc import lut
from altrepo_api.libs.pagination import Paginator

from .common import ErrataID, get_erratas_by_search_conditions
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


class FindErratas(APIWorker):
    """
    Erratas search lookup by id, vulnerability id or package name.
    """

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def check_params(self) -> bool:
        if self.args["input"] and len(self.args["input"]) > 3:
            self.validation_results.append(
                "input values list should contain no more than 3 elements"
            )

        if self.validation_results != []:
            return False
        return True

    def get(self):
        input_val: list[str] = self.args["input"] if self.args["input"] else []
        branch = self.args["branch"]
        eh_type = lut.known_errata_type.get(self.args["type"], "")
        limit = self.args["limit"]
        page = self.args["page"]
        is_discarded = self.args["is_discarded"]

        branch_clause = f"AND pkgset_name = '{branch}'" if branch else ""
        where_conditions = [f"type IN {eh_type}"] if eh_type else []
        if is_discarded:
            where_conditions.append(f"discard = {is_discarded}")

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
            where_conditions.append(f"({' OR '.join(conditions)})")

        where_clause = (
            f"WHERE {' AND '.join(where_conditions)}" if where_conditions else ""
        )

        response = self.send_sql_request(
            self.sql.find_erratas.format(
                branch=branch_clause, where_clause=where_clause
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
            pkgs = [PackageInfo(*el)._asdict() for el in errata_info.pkgs]

            erratas.append(
                errata_info._replace(vulnerabilities=vulns, packages=pkgs)._asdict()
            )

        paginator = Paginator(erratas, limit)
        page_obj = paginator.get_page(page)

        res: dict[str, Any] = {
            "request_args": self.args,
            "erratas": page_obj,
            "length": len(page_obj),
        }

        return (
            res,
            200,
            {
                "Access-Control-Expose-Headers": "X-Total-Count",
                "X-Total-Count": int(paginator.count),
            },
        )
