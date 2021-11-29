# altrepodb API
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

import base64
from collections import namedtuple

from utils import datetime_to_iso

from api.base import APIWorker
from api.misc import lut
from ..sql import sql


class SpecfileByPackageName(APIWorker):
    """Retrieves spec file by source package name and branch."""

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        self.validation_results = []

        if self.args["branch"] not in lut.known_branches:
            self.validation_results.append(
                f"unknown package set name : {self.args['branch']}"
            )
            self.validation_results.append(
                f"allowed package set names are : {lut.known_branches}"
            )

        if self.args["name"] == "":
            self.validation_results.append(f"package name should not be empty string")

        if self.validation_results != []:
            return False
        else:
            return True

    def get(self):
        pkg_name = self.args["name"]
        branch = self.args["branch"]

        self.conn.request_line = self.sql.get_specfile_by_name.format(
            name=pkg_name, branch=branch
        )
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        if not response:
            self._store_error(
                {
                    "message": f"No specfile found for {pkg_name} in {branch}",
                    "args": self.args,
                },
                self.ll.INFO,
                404,
            )
            return self.error

        SpecFile = namedtuple(
            "SpecFile",
            [
                "pkg_hash",
                "pkg_name",
                "pkg_version",
                "pkg_release",
                "specfile_name",
                "specfile_date",
                "specfile_content",
                "content_length",
            ],
        )

        specfile = SpecFile(*response[0])._asdict()
        specfile["pkg_hash"] = str(specfile["pkg_hash"])
        specfile["specfile_date"] = datetime_to_iso(specfile["specfile_date"])
        # workaround for CH base64encode bug #30854
        data = base64.b64decode(specfile["specfile_content"])
        if len(data) != specfile["content_length"]:
            specfile["specfile_content"] = base64.b64encode(data[:specfile["content_length"]]).decode("utf-8")

        res = {
            "request_args": self.args,
            **specfile,
        }

        return res, 200


class SpecfileByPackageHash(APIWorker):
    """Retrieves spec file by source package name and branch."""

    def __init__(self, connection, pkghash, **kwargs):
        self.pkghash = pkghash
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def get(self):
        self.conn.request_line = self.sql.get_specfile_by_hash.format(
            pkghash=self.pkghash
        )
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        if not response:
            self._store_error(
                {
                    "message": f"No specfile found for package with hash {self.pkghash}",
                    "args": self.args,
                },
                self.ll.INFO,
                404,
            )
            return self.error

        SpecFile = namedtuple(
            "SpecFile",
            [
                "pkg_hash",
                "pkg_name",
                "pkg_version",
                "pkg_release",
                "specfile_name",
                "specfile_date",
                "specfile_content",
                "content_length",
            ],
        )

        specfile = SpecFile(*response[0])._asdict()
        specfile["pkg_hash"] = str(specfile["pkg_hash"])
        specfile["specfile_date"] = datetime_to_iso(specfile["specfile_date"])
        # workaround for CH base64encode bug #30854
        data = base64.b64decode(specfile["specfile_content"])
        if len(data) != specfile["content_length"]:
            specfile["specfile_content"] = base64.b64encode(data[:specfile["content_length"]]).decode("utf-8")

        res = {
            "request_args": self.args,
            **specfile,
        }

        return res, 200
