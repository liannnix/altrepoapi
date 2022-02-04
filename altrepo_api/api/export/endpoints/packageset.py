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

from collections import namedtuple

from altrepo_api.utils import datetime_to_iso

from altrepo_api.api.base import APIWorker
from altrepo_api.api.misc import lut
from ..sql import sql


class PackageSetBinaries(APIWorker):
    """Retrieves packageset binary packages info from DB."""

    def __init__(self, connection, branch, **kwargs):
        self.branch = branch
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        self.validation_results = []

        if self.branch == "" or self.branch not in lut.repology_export_branches:
            self.validation_results.append(
                f"unknown package set name : {self.branch}"
            )
            self.validation_results.append(
                f"allowed package set names are : {lut.repology_export_branches}"
            )

        if self.validation_results != []:
            return False
        else:
            return True

    def get(self):
        arch = self.args["arch"]
        arch_clause = ""
        if arch is not None:
            arch_clause = f"AND pkg_arch = '{arch}'"
        # get packages info
        self.conn.request_line = self.sql.get_branch_binary_packages.format(
            branch=self.branch, arch_clause=arch_clause
        )
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        if not response:
            self._store_error(
                {
                    "message": f"No data found for branch '{self.branch}'",
                    "args": self.args,
                },
                self.ll.INFO,
                404,
            )
            return self.error

        BinPkgInfo = namedtuple(
            "BinPkgInfo",
            [
                "name",
                "epoch",
                "version",
                "release",
                "arch",
                "disttag",
                "buildtime",
                "source",
            ],
        )
        packages = [BinPkgInfo(*el)._asdict() for el in response]

        res = {
            "branch": self.branch,
            "request_args": self.args,
            "length": len(packages),
            "packages": packages,
        }

        return res, 200
