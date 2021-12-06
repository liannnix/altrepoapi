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

from altrepo_api.utils import datetime_to_iso

from altrepo_api.api.base import APIWorker
from altrepo_api.api.misc import lut
from ..sql import sql


class MaintainerBeehiveErrors(APIWorker):
    """Retrieves maintainer's packages Beehive rebuild errors."""

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        self.validation_results = []

        if self.args["branch"] == "" or self.args["branch"] not in lut.known_beehive_branches:
            self.validation_results.append(
                f"unknown package set name : {self.args['branch']}"
            )
            self.validation_results.append(
                f"allowed package set names are : {lut.known_beehive_branches}"
            )

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
        branch = self.args["branch"]
        by_acl = self.args['by_acl']
        order_g = ""

        if by_acl == 'by_nick':
            self.conn.request_line = self.sql.get_beehive_errors_by_nick_acl.format(
                maintainer_nickname=maintainer_nickname, branch=branch
            )
        if by_acl == 'by_nick_leader':
            order_g = 'AND order_g = 0'
            self.conn.request_line = self.sql.get_beehive_errors_by_last_acl_with_group.format(
                maintainer_nickname=maintainer_nickname, branch=branch, order_g=order_g
            )
        if by_acl == 'by_nick_or_group':
            self.conn.request_line = self.sql.get_beehive_errors_by_nick_or_group_acl.format(
                maintainer_nickname=maintainer_nickname, branch=branch
            )
        if by_acl == 'by_nick_leader_and_group':
            self.conn.request_line = self.sql.get_beehive_errors_by_last_acl_with_group.format(
                maintainer_nickname=maintainer_nickname, branch=branch, order_g=order_g
            )
        if by_acl == 'none':
            self.conn.request_line = self.sql.get_beehive_errors_by_maintainer.format(
                maintainer_nickname=maintainer_nickname, branch=branch
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

        BeehiveStatus = namedtuple(
            "BeehiveStatus",
            [
                "hash",
                "branch",
                "name",
                "version",
                "release",
                "arch",
                "build_time",
                "updated",
                "ftbfs_since",
                "epoch",
            ]
        )
        res = [BeehiveStatus(*el)._asdict() for el in response]

        for el in res:
            epoch_ = el["epoch"]
            if epoch_ == 0:
                epoch_version = el["version"]
            else:
                epoch_version = str(epoch_) + ":" + el["version"]

            url = "/".join((
                lut.beehive_base,
                "logs",
                "Sisyphus" if el["branch"] == "sisyphus" else el["branch"],
                el["arch"],
                "archive",
                el["updated"].strftime("%Y/%m%d"),
                "error",
                "-".join((
                    el["name"],
                    epoch_version,
                    el["release"]
                )),
            ))
            el["url"] = url
            el["updated"] = datetime_to_iso(el["updated"])
            el["ftbfs_since"] = datetime_to_iso(el["ftbfs_since"])
            # el.pop("hash", None)
            # el.pop("epoch", None)

        res = {"request_args": self.args, "length": len(res), "beehive": res}

        return res, 200
