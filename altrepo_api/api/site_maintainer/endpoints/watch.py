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


class WatchByMaintainer(APIWorker):
    """Retrieves Watch results for maintainer's packages."""

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        self.validation_results = []

        if self.args["maintainer_nickname"] == "":
            self.validation_results.append(
                f"maintainer nickname should not be empty string"
            )

        if self.validation_results != []:
            return False
        else:
            return True

    def get(self):
        maintainer_nickname = self.args["maintainer_nickname"]

        MaintainerWatch = namedtuple(
            "MaintainerWatch",
            [
                "pkg_name",
                "old_version",
                "new_version",
                "url",
                "date_update"
            ],
        )

        if self.args['by_acl'] == 'by_nick_leader_and_group':
            self.conn.request_line = self.sql.get_watch_by_last_acl_with_group.format(
                maintainer_nickname=maintainer_nickname
            )
        if self.args['by_acl'] == 'by_nick_leader':
            self.conn.request_line = self.sql.get_watch_by_last_acl.format(
                maintainer_nickname=maintainer_nickname
            )
        if self.args['by_acl'] == 'by_nick':
            self.conn.request_line = self.sql.get_watch_by_nick_acl.format(
                maintainer_nickname=maintainer_nickname
            )
        if self.args['by_acl'] == 'by_nick_or_group':
            self.conn.request_line = self.sql.get_watch_by_nick_or_group_acl.format(
                maintainer_nickname=maintainer_nickname
            )
        if self.args['by_acl'] == 'none':
            self.conn.request_line = self.sql.get_watch_by_packager.format(
                maintainer_nickname=maintainer_nickname
            )

        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        if not response:
            self._store_error(
                {"message": f"No data not found in database", "args": self.args},
                self.ll.INFO,
                404,
            )
            return self.error
        res = [MaintainerWatch(*el)._asdict() for el in response]

        res = {"request_args": self.args, "length": len(res), "packages": res}

        return res, 200
