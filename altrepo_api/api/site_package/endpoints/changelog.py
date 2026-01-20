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

MAX_CHLOG_LENGTH = 1000


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

        chlog_length = self.args["changelog_last"]

        if chlog_length < 1 or chlog_length > MAX_CHLOG_LENGTH:
            self.validation_results.append(
                f"changelog history length should be in range 1 to {MAX_CHLOG_LENGTH}"
            )

        return self.validation_results == []

    def get(self):
        self.chlog_length = self.args["changelog_last"]

        response = self.send_sql_request(
            (
                self.sql.get_pkg_changelog,
                {"pkghash": self.pkghash, "limit": self.chlog_length},
            )
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {
                    "message": f"No packages found in last packages with hash {self.pkghash}",
                    "args": self.args,
                }
            )

        Changelog = namedtuple("Changelog", ["date", "name", "nick", "evr", "message"])
        changelog_list = [Changelog(*el[1:])._asdict() for el in response]

        res = {
            "pkghash": str(self.pkghash),
            "request_args": self.args,
            "length": len(changelog_list),
            "changelog": changelog_list,
        }

        return res, 200
