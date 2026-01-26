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

from altrepo_api.utils import join_tuples, valid_task_id
from altrepo_api.api.base import APIWorker

from ..sql import sql


class FindPackageset(APIWorker):
    """Retrieves packages information from package set by source packages from task."""

    def __init__(self, connection, id, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        self.task_id = id
        super().__init__()

    def check_task_id(self):
        if not valid_task_id(self.task_id):
            return False
        response = self.send_sql_request(self.sql.check_task.format(id=self.task_id))
        if not self.sql_status:
            return False

        return response[0][0] != 0

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        return True

    def get(self):
        response = self.send_sql_request(
            self.sql.task_src_packages.format(id=self.task_id)
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {
                    "message": f"No source packages found in database for task {self.task_id}"
                }
            )

        packages = join_tuples(response)

        if self.args["branches"]:
            branchs_cond = f"AND pkgset_name IN {tuple(self.args['branches'])}"
        else:
            branchs_cond = ""

        response = self.send_sql_request(
            (
                self.sql.get_branch_with_pkgs.format(branchs=branchs_cond),
                {"pkgs": packages},
            )
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {
                    "message": "No results found in last package sets for given parameters",
                    "args": self.args,
                }
            )

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

        res = {
            "id": self.task_id,
            "request_args": self.args,
            "task_packages": list(packages),
            "length": len(res),
            "packages": res,
        }

        return res, 200
