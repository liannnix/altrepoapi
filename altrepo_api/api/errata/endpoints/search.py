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

from altrepo_api.api.base import APIWorker

from .common import Errata, Reference
from ..sql import sql


class Search(APIWorker):
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
                self.args.get("errata_id"),
            )
        ):
            self.validation_results.append(
                "At least one of `branch`, `name` or `errata_id` argument should be specified"
            )
            return False
        return True

    def get(self):
        branch = self.args.get("branch")
        vuln_id = self.args.get("errata_id")
        package_name = self.args.get("name")

        search_conditions = []

        if branch is not None:
            search_conditions.append(f"pkgset_name = '{branch}'")

        if vuln_id is not None:
            search_conditions.append(
                f"arrayExists(x -> (x ILIKE '%{vuln_id}%'), eh_references.link)"
            )

        if package_name is not None:
            search_conditions.append(f"pkg_name LIKE '%{package_name}%'")

        where_clause = "AND "
        if search_conditions:
            where_clause += " AND ".join(search_conditions)

        response = self.send_sql_request(
            self.sql.search_valid_errata.format(where_clause=where_clause)
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {"message": f"No data not found in database for {self.args}"}
            )

        erratas: list[Errata] = sorted(
            (
                Errata(
                    row[0],  # errata_id
                    *row[1][:-2],  # errata details
                    [Reference(*el) for el in zip(row[1][-1], row[1][-2])],  # type: ignore
                )
                for row in response
            ),
            key=lambda x: x.task_changed,
            reverse=True,
        )

        return {"erratas": [errata.asdict() for errata in erratas]}, 200
