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


class PackagesByUuid(APIWorker):
    """
    Get packages from database by packageset component UUID.
    """

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def get(self):
        uuid = self.args["uuid"]

        response = self.send_sql_request(
            self.sql.get_packages_by_uuid.format(uuid=uuid),
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {
                    "message": "No data found in database",
                    "args": self.args,
                }
            )

        PkgMeta = namedtuple(
            "PkgMeta",
            [
                "hash",
                "pkg_name",
                "pkg_version",
                "pkg_release",
                "pkg_arch",
                "sourcerpm",
                "pkg_summary",
                "pkg_buildtime",
                "changelog_date",
                "changelog_name",
                "changelog_evr",
                "changelog_text",
            ],
        )

        retval = [PkgMeta(*el)._asdict() for el in response]

        res = {
            "request_args": self.args,
            "length": len(retval),
            "packages": retval,
        }
        return res, 200
