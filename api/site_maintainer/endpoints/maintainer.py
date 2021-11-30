# ALTRepo API
# Copyright (C) 2021  BaseALT Ltd

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

from api.base import APIWorker
from api.misc import lut
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
        self.validation_results = []

        if self.args["branch"] == "" or self.args["branch"] not in lut.known_branches:
            self.validation_results.append(
                f"unknown package set name : {self.args['branch']}"
            )
            self.validation_results.append(
                f"allowed package set names are : {lut.known_branches}"
            )

        if self.validation_results != []:
            return False
        else:
            return True

    def get(self):
        branch = self.args["branch"]
        self.conn.request_line = self.sql.get_all_maintaners.format(
            branch=branch, where_clause=""
        )
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        if not response:
            self._store_error(
                {"message": f"No data not found in database", "args": self.args},
                self.ll.INFO,
                404,
            )
            return self.error

        res = [
            {"packager_name": m[0], "packager_nickname": m[1], "count_source_pkg": m[2]}
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
        self.validation_results = []

        if self.args["branch"] == "" or self.args["branch"] not in lut.known_branches:
            self.validation_results.append(
                f"unknown package set name : {self.args['branch']}"
            )
            self.validation_results.append(
                f"allowed package set names are : {lut.known_branches}"
            )

        if self.args["maintainer_nickname"] == "":
            self.validation_results.append(
                f"maintainer nickname should not be empty string"
            )

        if self.validation_results != []:
            return False
        else:
            return True

    def get(self):
        maintainer_nickname = self.args["maintainer_nickname"]
        branch = self.args["branch"]
        where_clause = "WHERE packager_nick = %(nickname)s"
        self.conn.request_line = (
            self.sql.get_all_maintaners.format(
                branch=branch, where_clause=where_clause
            ),
            {"nickname": maintainer_nickname},
        )
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        if not response or response[0][0] == []:
            self._store_error(
                {
                    "message": f"No data found in database for {maintainer_nickname} on {branch}",
                    "args": self.args,
                },
                self.ll.INFO,
                404,
            )
            return self.error

        MaintainersInfo = namedtuple(
            "MaintainersInfoModel",
            [
                "packager_name",
                "packager_nickname",
                "count_source_pkg"
            ],
        )
        res = MaintainersInfo(*response[0])._asdict()
        res = {"request_args": self.args, "information": res}

        return res, 200
