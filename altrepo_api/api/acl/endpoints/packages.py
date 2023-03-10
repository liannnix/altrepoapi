# ALTRepo API
# Copyright (C) 2023  BaseALT Ltd

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

from typing import NamedTuple
from datetime import datetime

from altrepo_api.api.base import APIWorker
from ..sql import sql


class AclByPackages(APIWorker):
    """Retrieves ACL members list for specific packages and branch."""

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def get(self):
        class Package(NamedTuple):
            name: str
            updated: datetime
            members: list[str]

        branch = self.args["branch"]
        packages_names = tuple(self.args["packages_names"])

        _tmp_table = "tmp_pkgs_names"
        response = self.send_sql_request(
            self.sql.get_acl_by_packages.format(branch=branch, tmp_table=_tmp_table),
            external_tables=[
                {
                    "name": _tmp_table,
                    "structure": [
                        ("pkg_name", "String"),
                    ],
                    "data": [{"pkg_name": pkg_name} for pkg_name in packages_names],
                },
            ],
        )
        if not self.sql_status:
            return self.error

        packages = [Package(*r) for r in response]

        res = {
            "branch": branch,
            "packages": sorted(
                [r._asdict() for r in packages], key=lambda p: p["name"]
            ),
        }

        return res, 200
