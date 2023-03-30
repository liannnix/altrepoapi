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
from collections import namedtuple

from altrepo_api.api.base import APIWorker
from ..sql import sql


class PackagesByFile(APIWorker):
    """
    Find packages by file name.
    """

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def get(self):
        file_name = self.args["file_name"].replace("_", r"\_")
        branch = self.args["branch"]

        pkg_hshs = self.send_sql_request(
            self.sql.find_pkg_hshs_by_file.format(
                branch=branch, file_name=file_name,
            )
        )
        if not self.sql_status:
            return self.error
        if not pkg_hshs:
            return self.store_error(
                {"message": "No data not found in database"},
            )

        _tmp_table = "tmp_pkghash"

        response = self.send_sql_request(
            self.sql.get_packages.format(branch=branch, tmp_table=_tmp_table),
            external_tables=[
                {
                    "name": _tmp_table,
                    "structure": [
                        ("pkg_hash", "UInt64"),
                    ],
                    "data": pkg_hshs,
                }
            ],
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {"message": "No data not found in database"},
            )

        PkgMeta = namedtuple(
            "PkgMeta",
            [
                "hash",
                "name",
                "version",
                "release",
                "arch"
            ],
        )

        packages = [PkgMeta(*el)._asdict() for el in response]

        res = {
            "request_args": self.args,
            "length": len(packages),
            "packages": packages
        }
        return res, 200
