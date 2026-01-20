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

from altrepo_api.utils import full_file_permissions, bytes2human

from altrepo_api.api.base import APIWorker
from ..sql import sql


class PackageFiles(APIWorker):
    """Retrieves package files information by hash"""

    def __init__(self, connection, pkghash, **kwargs):
        self.conn = connection
        self.pkghash = pkghash
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def get(self):
        response = self.send_sql_request(
            self.sql.get_pkg_files.format(pkghash=self.pkghash)
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {
                    "message": f"No information found in DB for package hash {self.pkghash}",
                    "args": self.pkghash,
                }
            )

        PkgFiles = namedtuple(
            "PkgFiles",
            [
                "file_name",
                "file_size",
                "file_class",
                "symlink",
                "file_mtime",
                "file_mode",
            ],
        )
        pkg_files = [PkgFiles(*el)._asdict() for el in response]

        for elem in pkg_files:
            elem["file_mode"] = full_file_permissions(
                elem["file_class"], elem["file_mode"]
            )
            elem["file_size"] = bytes2human(elem["file_size"])

        res = {
            "request_args": self.pkghash,
            "length": len(pkg_files),
            "files": pkg_files,
        }
        return res, 200
