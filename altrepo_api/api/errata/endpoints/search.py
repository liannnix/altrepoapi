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

from typing import NamedTuple

from altrepo_api.api.base import APIWorker

from .common import ErrataID, get_erratas_by_search_conditions
from ..sql import sql


_vuln_id_match = re.compile(r"(^CVE-\d{4}-\d{4,}$)|(^BDU:\d{4}-\d{5}$)|(^\d{4,}$)")


class ErrataInfo(NamedTuple):
    errata_id: str
    eh_type: str
    task_id: int
    branch: str
    vuln_numbers: list
    vuln_types: list
    changed: str
    vulnerabilities: list[dict[str, str]] = []


class Vulns(NamedTuple):
    number: str
    type: str


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
        input_val: list[str] = self.args["input"][:] if self.args["input"] else []
        branch = self.args["branch"]
        eh_type = self.args["type"]

        branch_clause = f"AND pkgset_name = '{branch}'" if branch else ""
        eh_type_clause = f" (type = '{eh_type}') AND " if eh_type else ""

        conditions = [
            " OR ".join(
                (
                    f"(errata_id ILIKE '%{v}%')",
                    f"(pkg_name ILIKE '%{v}%')",
                    f"arrayExists(x -> x ILIKE '%{v}%', refs_links)",
                )
            )
            for v in input_val[:]
        ]

        where_clause = "WHERE " + eh_type_clause + f"({' OR '.join(conditions)})"

        response = self.send_sql_request(
            self.sql.find_erratas.format(branch=branch_clause, where=where_clause)
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {"message": "No data not found in database"},
            )

        erratas = []
        for el in response:
            errata_inf = ErrataInfo(*el)
            vulns = [
                Vulns(vuln, errata_inf.vuln_types[i])._asdict()
                for i, vuln in enumerate(errata_inf.vuln_numbers)
            ]
            erratas.append(errata_inf._replace(vulnerabilities=vulns)._asdict())

        res = {"request_args": self.args, "length": len(erratas), "erratas": erratas}

        return res, 200
