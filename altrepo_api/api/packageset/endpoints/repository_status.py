# ALTRepo API
# Copyright (C) 2021-2022  BaseALT Ltd

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
from collections import namedtuple

from altrepo_api.utils import sort_branches
from altrepo_api.api.base import APIWorker
from ..sql import sql


class RepositoryStatistics(APIWorker):
    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def get(self):
        branch = self.args["branch"]
        if branch:
            branch_clause = f"AND pkgset_nodename = '{branch}'"
        else:
            branch_clause = ""

        response = self.send_sql_request(
            self.sql.get_repository_package_counts.format(branch=branch_clause),
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {
                    "message": "No data found in database",
                    "args": self.args,
                }
            )

        PkgCount = namedtuple("PkgCount", ["arch", "component", "count"])

        branches = []
        for branch in sort_branches([el[0] for el in response]):
            for el in response:
                if el[0] == branch:
                    counts = {
                        "branch": el[0],
                        "date_update": el[1],
                        "packages_count": [PkgCount(*x)._asdict() for x in el[2]],
                    }
                    branches.append(counts)
                    break

        res = {"length": len(branches), "branches": branches}
        return res, 200
