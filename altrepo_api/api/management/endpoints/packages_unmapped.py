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

from altrepo_api.api.base import APIWorker
from altrepo_api.api.misc import lut
from altrepo_api.settings import namespace as settings

from ..sql import sql


class PackagesUnmapped(APIWorker):
    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        return True

    def get(self):
        pkg_names = self.args["name"]
        name_like_clause = " AND ".join([f"pkg_name ILIKE '%{n}%'" for n in pkg_names])

        if settings.FEATURE_FLAGS.get(lut.feature_pnc_multi_mapping, False):
            response = self.send_sql_request(
                self.sql.get_all_packages.format(
                    name_like=name_like_clause,
                    branches=list(lut.branch_inheritance.keys()),
                )
            )
        else:
            response = self.send_sql_request(
                self.sql.get_unmapped_packages.format(
                    name_like=name_like_clause,
                    branches=list(lut.branch_inheritance.keys()),
                    pnc_branches=lut.repology_branches,
                )
            )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {"message": "No packages not found in database", "args": self.args},
            )

        pkgs = [el[0] for el in response]
        res = {"request_args": self.args, "length": len(pkgs), "packages": pkgs}
        return res, 200
