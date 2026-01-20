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
from altrepo_api.api.misc import lut
from ..sql import sql


class UnpackagedDirs(APIWorker):
    """Retrieves upackaged directories by packager."""

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        return True

    def get(self):
        self.packager = self.args["packager"]
        self.branch = self.args["branch"]
        self.archs = self.args["archs"]
        if self.archs:
            if "noarch" not in self.archs:
                self.archs.append("noarch")
        else:
            self.archs = lut.default_archs
        self.archs = tuple(self.archs)

        response = self.send_sql_request(
            (
                self.sql.get_unpackaged_dirs,
                {
                    "branch": self.branch,
                    "email": "{}@%".format(self.packager),
                    "archs": self.archs,
                },
            )
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {
                    "message": "No data found in database for given parameters",
                    "args": self.args,
                }
            )

        DirsInfo = namedtuple(
            "DirsInfo",
            [
                "package",
                "directory",
                "version",
                "release",
                "epoch",
                "packager",
                "email",
                "archs",
            ],
        )

        retval = [DirsInfo(*el)._asdict() for el in response]

        res = {"request_args": self.args, "length": len(retval), "packages": retval}
        return res, 200
