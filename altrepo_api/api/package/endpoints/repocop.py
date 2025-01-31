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
        self.packages = []
        super().__init__()

    def check_params_post(self):
        self.validation_results = []

        for elem in self.args["json_data"]["packages"]:
            pkg = elem.copy()
            try:
                pkg["rc_test_date"] = dt.datetime.fromisoformat(pkg["rc_test_date"])
                self.packages.append(pkg)
            except (TypeError, ValueError):
                self.validation_results.append(f"Invalid data: {elem}")
                break

        if self.validation_results != []:
            return False
        else:
            return True

    def check_params_get(self):
        self.logger.debug(f"args : {self.args}")
        return True

    def post(self):
        _ = self.send_sql_request((self.sql.insert_into_repocop, self.packages))
        if not self.sql_status:
            return self.error

        return "data loaded successfully", 201

    def get(self):
        pkg_name = self.args["package_name"]
        pkg_version = self.args["package_version"]
        pkg_release = self.args["package_release"]
        bin_pkg_arch = self.args["bin_package_arch"]
        branch = self.args["branch"]
        is_source = {"source": 1, "binary": 0}[self.args["package_type"]]

        version_cond = ""
        release_cond = ""
        arch_cond = ""

        if is_source == 1:
            name_cond = f"""
pkg_name IN (
    SELECT pkg_name
    FROM PackagesRepocop
    WHERE rc_srcpkg_name = '{pkg_name}'
)
"""

            if pkg_version is not None:
                version_cond = f"AND rc_srcpkg_version = '{pkg_version}'"

            if pkg_release is not None:
                release_cond = f"AND rc_srcpkg_release = '{pkg_release}'"
        else:
            name_cond = f"pkg_name = '{pkg_name}'"

            if pkg_version is not None:
                version_cond = f"AND pkg_version = '{pkg_version}'"

            if pkg_release is not None:
                release_cond = f"AND pkg_release = '{pkg_release}'"

        if bin_pkg_arch is not None:
            arch_cond = f"AND pkg_arch = '{bin_pkg_arch}'"

        response = self.send_sql_request(
            self.sql.get_last_repocop_results.format(
                pkgs=name_cond,
                srcpkg_version=version_cond,
                srcpkg_release=release_cond,
                branch=branch,
                arch=arch_cond,
            )
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {
                    "message": "No results found in database for given parameters",
                    "args": self.args,
                }
            )

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
