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

from altrepo_api.api.base import APIWorker
from ..sql import sql


class FindSourcePackageInBranch(APIWorker):
    """Find source package in branch by package name"""

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

        # get source package name from static_last_packages
        response = self.send_sql_request(
            self.sql.get_source_pkg_name.format(name=name, branch=branch)
        )
        if not self.sql_status:
            return self.error

        if response:
            src_pkg_name = response[0][0]
        else:
            # nothing found -> find source package name in the BranchPackageHistory
            response = self.send_sql_request(
                self.sql.get_src_pkg_by_bin.format(name=name, branch=branch)
            )
            if not self.sql_status:
                return self.error
            if not response:
                return self.store_error(
                    {
                        "message": f"No information found for {name} in DB",
                        "args": self.args,
                    }
                )
            src_pkg_name = response[0][0]

        res = {
            "request_args": self.args,
            "source_package": src_pkg_name,
        }

        return res, 200
