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

from altrepo_api.utils import sort_branches, bytes2human
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
            branch_clause = f"WHERE branch = '{branch}'"
        else:
            branch_clause = ""

        response = self.send_sql_request(
            self.sql.get_repository_statistics.format(branch=branch_clause),
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

        BranchStats = namedtuple("BranchStats", ["branch", "date", "stats"])
        PkgCount = namedtuple("PkgCount", ["arch", "component", "count", "size", "uuid"])

        res = []
        branches = [BranchStats(*el) for el in response]
        for branch in sort_branches([b.branch for b in branches]):
            for b in branches:
                if b.branch == branch:
                    stats = [PkgCount(*x)._asdict() for x in b.stats]
                    for s in stats:
                        # convert total file size to human readable
                        s["size_hr"] = bytes2human(s["size"])
                        # replace arch for source packages component
                        if s["component"] == "srpm":
                            s["arch"] = "srpm"

                    counts = {
                        "branch": b.branch,
                        "date_update": b.date,
                        "packages_count": sorted(
                            stats, key=lambda x: (x["arch"], x["component"])
                        ),
                    }

                    res.append(counts)
                    break

        return {"length": len(res), "branches": res}, 200
