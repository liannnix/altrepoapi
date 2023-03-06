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

from collections import namedtuple

from altrepo_api.api.base import APIWorker
from ..sql import sql


class MaintainerPackages(APIWorker):
    """Retrieves maintainer's packages information from last package sets."""

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
        branch = self.args["branch"]
        by_acl = self.args["by_acl"]
        request_line = ""

        if by_acl == "by_nick":
            request_line = self.sql.get_maintainer_pkg_by_nick_acl.format(
                maintainer_nickname=maintainer_nickname, branch=branch
            )
        if by_acl == "by_nick_leader":
            request_line = self.sql.get_maintainer_pkg_by_nick_leader_acl.format(
                maintainer_nickname=maintainer_nickname, branch=branch
            )
        if by_acl == "by_nick_or_group":
            request_line = self.sql.get_maintainer_pkg_by_nick_or_group_acl.format(
                maintainer_nickname=maintainer_nickname, branch=branch
            )
        if by_acl == "by_nick_leader_and_group":
            request_line = (
                self.sql.get_maintainer_pkg_by_nick_leader_and_group_acl.format(
                    maintainer_nickname=maintainer_nickname, branch=branch
                )
            )
        if by_acl == "none":
            request_line = self.sql.get_maintainer_pkg.format(
                maintainer_nickname=maintainer_nickname, branch=branch
            )

        response = self.send_sql_request(request_line)
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {"message": "No data not found in database", "args": self.args}
            )

        MaintainerPackages = namedtuple(
            "MaintainerPackagesModel",
            ["name", "buildtime", "url", "summary", "version", "release"],
        )

        res = [MaintainerPackages(*el)._asdict() for el in response]
        res = {"request_args": self.args, "length": len(res), "packages": res}

        return res, 200
