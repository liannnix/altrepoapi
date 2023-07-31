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

from typing import NamedTuple

from altrepo_api.api.base import APIWorker
from ..sql import sql


class ErrataInfo(NamedTuple):
    errata_id: str
    eh_type: str
    task_id: int
    branch: str
    pkgs: list
    vuln_numbers: list
    vuln_types: list
    changed: str
    vulnerabilities: list[dict[str, str]] = []
    packages: list[dict[str, str]] = []


class Vulns(NamedTuple):
    number: str
    type: str


class PackageInfo(NamedTuple):
    pkghash: int
    pkg_name: str
    pkg_version: str
    pkg_release: str


class ErrataLastChanged(APIWorker):
    """Retrieves last changed errata."""

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def get(self):
        branch = self.args["branch"]
        eh_type = self.args["type"]
        limit = self.args["limit"]
        branch_clause = f"AND pkgset_name = '{branch}'" if branch else ""
        limit_clause = f"LIMIT {limit}" if limit else ""
        eh_type_clause = f"WHERE type = '{eh_type}'" if eh_type else ""

        response = self.send_sql_request(
            self.sql.get_last_changed_errata.format(
                branch=branch_clause, eh_type=eh_type_clause, limit=limit_clause
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
            errata_inf = ErrataInfo(*el)
            vulns = [
                Vulns(vuln, errata_inf.vuln_types[i])._asdict()
                for i, vuln in enumerate(errata_inf.vuln_numbers)
            ]
            pkgs = [PackageInfo(*el)._asdict() for el in errata_inf.pkgs]

            erratas.append(
                errata_inf._replace(vulnerabilities=vulns, packages=pkgs)._asdict()
            )

        res = {"request_args": self.args, "length": len(erratas), "erratas": erratas}

        return res, 200
