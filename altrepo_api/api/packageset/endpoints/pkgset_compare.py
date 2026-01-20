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


class PackagesetCompare(APIWorker):
    """Compares two package set packages."""

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        return True

    def get(self):
        self.pkgset1 = self.args["pkgset1"]
        self.pkgset2 = self.args["pkgset2"]

        response = self.send_sql_request(
            (
                self.sql.get_compare_info,
                {"pkgset1": self.pkgset1, "pkgset2": self.pkgset2},
            )
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {
                    "message": "No data found in database for given parameters",
                    "args": self.args,
                }
            )

        Package = namedtuple("Package", ["name", "version", "release"])
        retval = []

        for el in response:
            retval.append(
                {
                    "pkgset1": self.pkgset1,
                    "pkgset2": self.pkgset2,
                    "package1": Package(*el[:3])._asdict(),
                    "package2": Package(*el[3:])._asdict(),
                }
            )

        res = {"request_args": self.args, "length": len(retval), "packages": retval}
        return res, 200
