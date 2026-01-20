# ALTRepo API
# Copyright (C) 2021-2026  BaseALT Ltd

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


class AllMaintainers(APIWorker):
    """Retrieves all maintainers information from last package sets."""

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

        response = self.send_sql_request(
            self.sql.get_all_maintaners.format(branch=branch, where_clause="")
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {"message": "No data not found in database", "args": self.args},
            )

        res = [
            {"packager_name": m[0], "packager_nickname": m[1], "count_source_pkg": m[2]}  # type: ignore
            for m in response
        ]

        res = {"request_args": self.args, "length": len(res), "maintainers": res}

        return res, 200


class MaintainerInfo(APIWorker):
    """Retrieves maintainer's packages summary from last package sets."""

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
        where_clause = "WHERE packager_nick = %(nickname)s"

        response = self.send_sql_request(
            (
                self.sql.get_all_maintaners.format(
                    branch=branch, where_clause=where_clause
                ),
                {"nickname": maintainer_nickname},
            )
        )
        if not self.sql_status:
            return self.error
        if not response or response[0][0] == []:  # type: ignore
            return self.store_error(
                {
                    "message": f"No data found in database for {maintainer_nickname} on {branch}",
                    "args": self.args,
                }
            )

        MaintainersInfo = namedtuple(
            "MaintainersInfoModel",
            ["packager_name", "packager_nickname", "count_source_pkg"],
        )

        res = {
            "request_args": self.args,
            "information": MaintainersInfo(*response[0])._asdict(),
        }

        return res, 200
