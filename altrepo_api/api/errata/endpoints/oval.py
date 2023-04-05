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
from altrepo_api.api.misc import lut
from ..sql import sql


class OvalExport(APIWorker):
    """Retrieves OVAL definitions of closed issues of branch packages from database."""

    def __init__(self, connection, branch, **kwargs):
        self.branch = branch
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        self.validation_results = []

        if self.branch not in lut.oval_export_branches:
            self.validation_results.append(f"unknown package set name : {self.branch}")
            self.validation_results.append(
                f"allowed package set names are : {lut.oval_export_branches}"
            )

        if self.validation_results != []:
            return False

        return True

    def get(self):
        package_name = self.args["package_name"] or "null"

        res = {
            "branch": self.branch,
            "request_args": self.args,
            "length": 0,
            "definitions": [
                {
                    "branch": self.branch
                },
                {
                    "package_name": package_name
                }
            ]
        }
        return res, 200
