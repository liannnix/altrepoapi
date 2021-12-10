# ALTRepo API
# Copyright (C) 2021  BaseALT Ltd

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


class FindPackageset(APIWorker):
    """Retrieves binary packages in package sets by source packages."""
    
    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        return True

    def get(self):
        self.packages = tuple(self.args["packages"])
        if self.args["branches"]:
            branchs_cond = f"AND pkgset_name IN {tuple(self.args['branches'])}"
        else:
            branchs_cond = ""

        self.conn.request_line = (
            self.sql.get_branch_with_pkgs.format(branchs=branchs_cond),
            {"pkgs": self.packages},
        )
        status, response = self.conn.send_request()
        if status is False:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error

        if not response:
            self._store_error(
                {
                    "message": f"No results found in last package sets for given parameters",
                    "args": self.args,
                },
                self.ll.INFO,
                404,
            )
            return self.error

        PkgsetInfo = namedtuple(
            "PkgsetInfo",
            [
                "branch",
                "sourcepkgname",
                "pkgset_datetime",
                "packages",
                "version",
                "release",
                "disttag",
                "packager_email",
                "buildtime",
                "archs",
            ],
        )

        res = [PkgsetInfo(*el)._asdict() for el in response]

        res = {"request_args": self.args, "length": len(res), "packages": res}

        return res, 200
