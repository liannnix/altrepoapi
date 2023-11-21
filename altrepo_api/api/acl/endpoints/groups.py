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
            request_line = self.sql.get_acl_group.format(branch=branch, acl_group=name)
        else:
            request_line = self.sql.get_all_acl_groups.format(branch=branch)

        response = self.send_sql_request(request_line)
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {"message": "No data not found in database", "args": self.args}
            )

        res = [
            {"group": m[0], "maintainers": m[1], "date": m[2]}  # type: ignore
            for m in response
        ]

        res = {"request_args": self.args, "length": len(res), "groups": res}

        return res, 200


class MaintainerGroups(APIWorker):
    """List the ACL groups that the given user belongs to."""

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        return True

    def get(self):
        branches = self.args["branch"]
        nickname = self.args["nickname"]

        branches_clause = ""
        if branches:
            branches_clause = f"AND (acl_branch IN {tuple(branches)})"

        response = self.send_sql_request(
            self.sql.get_groups_by_nickname.format(
                nickname=nickname, branches_clause=branches_clause
            ),
        )
        if not self.sql_status:
            return self.error

        result = {
            "nickname": nickname,
            "branches": [{"name": name, "groups": groups} for name, groups in response],
        }

        return result, 200
