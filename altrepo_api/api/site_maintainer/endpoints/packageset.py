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

from collections import namedtuple

from altrepo_api.utils import sort_branches

from altrepo_api.api.base import APIWorker
from ..sql import sql


class MaintainerBranches(APIWorker):
    """Retrieves maintainer's packages summary by branches from last package sets."""

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        return True

    def get(self):
        maintainer_nickname = self.args["maintainer_nickname"]

        response = self.send_sql_request(
            self.sql.get_maintainer_branches.format(
                maintainer_nickname=maintainer_nickname
            )
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {"message": "No data not found in database", "args": self.args}
            )

        MaintainerBranches = namedtuple("MaintainerBranches", ["branch", "count"])
        branches = []

        for branch in sort_branches([el[0] for el in response]):
            for el in [MaintainerBranches(*b)._asdict() for b in response]:
                if el["branch"] == branch:
                    branches.append(el)
                    break

        res = {"request_args": self.args, "length": len(branches), "branches": branches}

        return res, 200
