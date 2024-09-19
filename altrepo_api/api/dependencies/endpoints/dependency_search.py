# ALTRepo API
# Copyright (C) 2021-2024  BaseALT Ltd

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

from ..sql import sql

MAX_LIMIT = 5_000


class FastDependencySearchLookup(APIWorker):
    """
    Fast search for dependencies by name.
    """

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        self.validation_results = []

        limit = self.args["limit"]
        if limit and (limit < 1 or limit > MAX_LIMIT):
            self.validation_results.append(f"limit should be in range 1 to {MAX_LIMIT}")

        return self.validation_results == []

    def get(self):
        dp_name = self.args["dp_name"].replace("_", r"\_")
        branch = self.args["branch"]
        limit = self.args["limit"]
        if limit:
            limit_clause = f"LIMIT {limit}"
        else:
            limit_clause = ""

        response = self.send_sql_request(
            self.sql.fast_find_depends.format(
                dp_name=dp_name, branch=branch, limit=limit_clause
            )
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {"message": "No data not found in database"},
            )

        deps = [{"dp_name": el[0]} for el in response]

        res = {"request_args": self.args, "length": len(deps), "dependencies": deps}
        return res, 200
