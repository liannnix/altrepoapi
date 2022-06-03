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


class PackagesetPackageHash(APIWorker):
    """Retrieves package hash by package name in package set."""

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        return True

    def get(self):
        self.branch = self.args["branch"]
        self.name = self.args["name"]

        self.conn.request_line = self.sql.get_pkghash_by_name.format(
            branch=self.branch, name=self.name
        )
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        if not response:
            self._store_error(
                {
                    "message": f"Package '{self.name}' not found in package set '{self.branch}'",
                    "args": self.args,
                },
                self.ll.INFO,
                404,
            )
            return self.error

        res = {
            "request_args": self.args,
            "pkghash": str(response[0][0]),  # type: ignore
            "version": response[0][1],  # type: ignore
            "release": response[0][2],  # type: ignore
        }
        return res, 200


class PackagesetPackageBinaryHash(APIWorker):
    """Retrieves package hash by package binary name in package set."""

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        return True

    def get(self):
        self.branch = self.args["branch"]
        self.arch = self.args["arch"]
        self.name = self.args["name"]

        self.conn.request_line = self.sql.get_pkghash_by_binary_name.format(
            branch=self.branch, arch=self.arch, name=self.name
        )
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        if not response:
            self._store_error(
                {
                    "message": f"Package '{self.name}' architecture {self.arch} not found in package set '{self.branch}'",
                    "args": self.args,
                },
                self.ll.INFO,
                404,
            )
            return self.error

        res = {
            "request_args": self.args,
            "pkghash": str(response[0][0]),  # type: ignore
            "version": response[0][1],  # type: ignore
            "release": response[0][2],  # type: ignore
        }
        return res, 200
