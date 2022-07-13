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

from altrepo_api.api.base import APIWorker
from ..sql import sql


class AclGroups(APIWorker):
    """Retrieves ACL groups information for specific branch."""

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        return True

    def get(self):
        branch = self.args["branch"]
        name = self.args["name"]
        if name is not None:
            if name.startswith("@"):
                name = name[1:]
            self.conn.request_line = self.sql.get_acl_group.format(
                branch=branch, acl_group=name
            )
        else:
            self.conn.request_line = self.sql.get_all_acl_groups.format(branch=branch)

        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        if not response:
            self._store_error(
                {"message": "No data not found in database", "args": self.args},
                self.ll.INFO,
                404,
            )
            return self.error

        res = [
            {"group": m[0], "maintainers": m[1], "date": m[2]}  # type: ignore
            for m in response
        ]

        res = {"request_args": self.args, "length": len(res), "groups": res}

        return res, 200
