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
from altrepo_api.api.misc import lut
from ..sql import sql


class BinaryPackageLog(APIWorker):
    """Gets a link to the binary package build log"""

    def __init__(self, connection, pkghash, **kwargs):
        self.pkghash = pkghash
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def get(self):
        response = self.send_sql_request(
            self.sql.get_bin_pkg_log.format(pkghash=self.pkghash)
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {"message": f"No data not found in database for {self.pkghash}"}
            )

        BuildLog = namedtuple(
            "BuildLog",
            [
                "task_id",
                "subtask_id",
                "subtask_arch",
                "buildlog_hash",
            ],
        )

        res = BuildLog(*response[0])  # type: ignore
        return {
            "pkg_hash": str(self.pkghash),
            "task_id": res.task_id,
            "subtask_id": res.subtask_id,
            "subtask_arch": res.subtask_arch,
            "buildlog_hash": str(res.buildlog_hash),
            "link": f"{lut.gitalt_base}/tasks/{str(res.task_id)}/build/{str(res.subtask_id)}/{res.subtask_arch}/log",
        }, 200
