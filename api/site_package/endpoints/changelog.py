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

from api.base import APIWorker
from ..sql import sql


class PackageChangelog(APIWorker):
    """Retrieves package changelog from DB."""

    def __init__(self, connection, pkghash, **kwargs):
        self.pkghash = pkghash
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        self.validation_results = []

        if self.args["changelog_last"] < 1:
            self.validation_results.append(
                f"changelog history length should be not less than 1"
            )

        if self.validation_results != []:
            return False
        else:
            return True

    def get(self):
        self.chlog_length = self.args["changelog_last"]
        self.conn.request_line = (
            self.sql.get_pkg_changelog,
            {"pkghash": self.pkghash, "limit": self.chlog_length},
        )
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        if not response:
            self._store_error(
                {
                    "message": f"No packages found in last packages with hash {self.pkghash}",
                    "args": self.args,
                },
                self.ll.INFO,
                404,
            )
            return self.error

        Changelog = namedtuple("Changelog", ["date", "name", "evr", "message"])
        changelog_list = [Changelog(*el[1:])._asdict() for el in response]

        res = {
            "pkghash": str(self.pkghash),
            "request_args": self.args,
            "length": len(changelog_list),
            "changelog": changelog_list,
        }

        return res, 200
