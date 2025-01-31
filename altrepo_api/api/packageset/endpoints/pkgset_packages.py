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

from collections import namedtuple

from altrepo_api.api.base import APIWorker
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

        # ignore 'archs' argument if package type is "source" or "all"
        if self.pkg_type in ("source", "all"):
            archs = ""
        elif self.archs:
            if "noarch" not in self.archs:
                self.archs.append("noarch")
            archs = f"AND pkg_arch IN {tuple(self.archs)}"
        else:
            archs = ""

        depends_type_to_sql = {"source": (1,), "binary": (0,), "all": (1, 0)}
        sourcef = depends_type_to_sql[self.pkg_type]

        response = self.send_sql_request(
            self.sql.get_repo_packages.format(
                branch=self.branch, src=sourcef, archs=archs
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
