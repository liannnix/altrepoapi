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

import datetime as dt
from collections import namedtuple

from altrepo_api.api.base import APIWorker
from ..sql import sql


class Repocop(APIWorker):
    """Stores and retrieves Repocop tests results."""

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def check_params_post(self):
        self.validation_results = []
        self.input_params = []
        self.known_param = [
            "pkg_name",
            "pkg_version",
            "pkg_release",
            "pkg_arch",
            "pkgset_name",
            "rc_srcpkg_name",
            "rc_srcpkg_version",
            "rc_srcpkg_release",
            "rc_test_name",
            "rc_test_status",
            "rc_test_message",
            "rc_test_date",
        ]

        for elem in self.args["json_data"]["packages"]:
            for key in elem.keys():
                self.input_params.append(key)

        if set(self.input_params) != set(self.known_param):
            self.validation_results.append(f"allowable values : {self.known_param}")

        if self.validation_results != []:
            return False
        else:
            return True

    def check_params_get(self):
        self.logger.debug(f"args : {self.args}")
        return True

    def post(self):
        json_ = self.args["json_data"]["packages"]
        for el in json_:
            el["rc_test_date"] = dt.datetime.fromisoformat(el["rc_test_date"])
        self.conn.request_line = (self.sql.insert_into_repocop, json_)
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        return "data loaded successfully", 201

    def get(self):
        self.source_pakage = self.args["package_name"]
        branch = self.args["branch"]
        self.pkg_type = self.args["package_type"]

        pkg_type_to_sql = {"source": 1, "binary": 0}
        source = pkg_type_to_sql[self.pkg_type]

        version_cond = ""
        release_cond = ""
        arch_cond = ""
        if source == 1:
            name_cond = f"AND rc_srcpkg_name = '{self.args['package_name']}'"
            if self.args["package_version"] is not None:
                version_cond = (
                    f"AND rc_srcpkg_version = '{self.args['package_version']}'"
                )

            if self.args["package_release"] is not None:
                release_cond = (
                    f"AND rc_srcpkg_release = '{self.args['package_release']}'"
                )
        else:
            name_cond = f"AND pkg_name = '{self.args['package_name']}'"
            if self.args["package_version"] is not None:
                version_cond = f"AND pkg_version = '{self.args['package_version']}'"

            if self.args["package_release"] is not None:
                release_cond = f"AND pkg_release = '{self.args['package_release']}'"

        if self.args["bin_package_arch"] is not None:
            arch_cond = f"AND pkg_arch = '{self.args['bin_package_arch']}'"

        self.conn.request_line = self.sql.get_out_repocop.format(
            pkgs=name_cond,
            srcpkg_version=version_cond,
            srcpkg_release=release_cond,
            branch=branch,
            arch=arch_cond,
        )

        status, response = self.conn.send_request()
        if status is False:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error

        if not response:
            self._store_error(
                {
                    "message": "No results found in database for given parameters",
                    "args": self.args,
                },
                self.ll.INFO,
                404,
            )
            return self.error

        RepocopInfo = namedtuple(
            "RepocopJsonModel",
            [
                "pkg_name",
                "pkg_version",
                "pkg_release",
                "pkg_arch",
                "branch",
                "test_name",
                "test_status",
                "test_message",
                "test_date",
            ],
        )

        res = [RepocopInfo(*el)._asdict() for el in response]
        res = {"request_args": self.args, "length": len(res), "packages": res}

        return res, 200
