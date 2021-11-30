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
from ..sql import sql
from utils import datetime_to_iso


class Bugzilla(APIWorker):
    """Retrieves information about Bugzilla registered bugs from database."""

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def check_params_maintainer(self):
        self.logger.debug(f"args : {self.args}")
        self.validation_results = []

        if self.args["maintainer_nickname"] == "":
            self.validation_results.append(
                f"maintainer nickname should not be empty string"
            )

        if self.validation_results != []:
            return False
        else:
            return True

    def check_params_srcpkg(self):
        self.logger.debug(f"args : {self.args}")
        self.validation_results = []

        if self.args["package_name"] == "":
            self.validation_results.append(
                f"Source package name should not be empty string"
            )

        if self.validation_results != []:
            return False
        else:
            return True

    def get_bug_by_package(self):
        package_name = self.args["package_name"]
        self.pkg_type = self.args["package_type"]
        pkg_type_to_sql = {"source": 1, "binary": 0}
        source = pkg_type_to_sql[self.pkg_type]
        if source == 1:
            self.conn.request_line = (
                self.sql.get_pkg_name_by_srcpkg,
                {"srcpkg_name": package_name},
            )
            status, response = self.conn.send_request()
            if not status:
                self._store_sql_error(response, self.ll.ERROR, 500)
                return self.error
            if not response or response[0][0] == []:
                self._store_error(
                    {
                        "message": f"No data found in database for {package_name} source package",
                        "args": self.args,
                    },
                    self.ll.INFO,
                    404,
                )
                return self.error
            packages = {el[0] for el in response}
            packages.add(package_name)
        else:
            packages = {package_name}
        self.conn.request_line = self.sql.get_bugzilla_info_by_srcpkg.format(
            packages=tuple(packages)
        )
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        if not response or response[0][0] == []:
            self._store_error(
                {
                    "message": f"No data found in database for packages: {packages}",
                    "args": self.args,
                },
                self.ll.INFO,
                404,
            )
            return self.error

        BugzillaInfo = namedtuple(
            "BugzillaInfoModel",
            [
                "id",
                "status",
                "resolution",
                "severity",
                "product",
                "component",
                "assignee",
                "reporter",
                "summary",
                "ts",
            ],
        )

        res = [BugzillaInfo(*el)._asdict() for el in response]
        for r in res:
            r["ts"] = datetime_to_iso(r["ts"])
        res = {"request_args": self.args, "length": len(res), "bugs": res}

        return res, 200

    def get_bug_by_maintainer(self):
        maintainer_nickname = self.args["maintainer_nickname"]
        self.conn.request_line = self.sql.get_bugzilla_info_by_maintainer.format(
            maintainer_nickname=maintainer_nickname
        )
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        if not response or response[0][0] == []:
            self._store_error(
                {
                    "message": f"No data found in database for {maintainer_nickname}",
                    "args": self.args,
                },
                self.ll.INFO,
                404,
            )
            return self.error

        BugzillaInfo = namedtuple(
            "BugzillaInfoModel",
            [
                "id",
                "status",
                "resolution",
                "severity",
                "product",
                "component",
                "assignee",
                "reporter",
                "summary",
                "ts",
            ],
        )
        res = [BugzillaInfo(*el)._asdict() for el in response]
        for r in res:
            r["ts"] = datetime_to_iso(r["ts"])
        res = {"request_args": self.args, "length": len(res), "bugs": res}

        return res, 200
