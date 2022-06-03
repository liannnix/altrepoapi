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

from altrepo_api.api.base import APIWorker
from altrepo_api.api.misc import lut
from ..sql import sql


class PackagesetPackages(APIWorker):
    """Retrieves package set packages information."""

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        return True

    def get(self):
        self.pkg_type = self.args["package_type"]
        self.branch = self.args["branch"]
        self.archs = self.args["archs"]
        if self.archs:
            if "noarch" not in self.archs:
                self.archs.append("noarch")
        else:
            self.archs = lut.known_archs
        self.archs = tuple(self.archs)

        depends_type_to_sql = {"source": (1,), "binary": (0,), "all": (1, 0)}
        sourcef = depends_type_to_sql[self.pkg_type]

        self.conn.request_line = self.sql.get_repo_packages.format(
            branch=self.branch, archs=self.archs, src=sourcef
        )

        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error

        if not response:
            self._store_error(
                {
                    "message": "No data found in database for given parameters",
                    "args": self.args,
                },
                self.ll.INFO,
                404,
            )
            return self.error

        PkgMeta = namedtuple(
            "PkgMeta",
            [
                "hash",
                "name",
                "version",
                "release",
                "summary",
                "maintainers",
                "url",
                "license",
                "category",
                "archs",
                "acl_list",
            ],
        )

        retval = [PkgMeta(*el)._asdict() for el in response]

        res = {"request_args": self.args, "length": len(retval), "packages": retval}
        return res, 200
