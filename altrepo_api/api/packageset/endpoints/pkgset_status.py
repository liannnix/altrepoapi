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

import base64
import binascii
import datetime as dt
import json
from collections import namedtuple

from altrepo_api.utils import sort_branches

from altrepo_api.api.base import APIWorker
from altrepo_api.api.misc import lut
from ..sql import sql


class RepositoryStatus(APIWorker):
    """
    Upload or get information on current repositories.
    """

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def check_params_post(self):
        self.logger.debug(f"args : {self.args}")
        self.validation_results = []
        self.input_params = []
        self.known_param = [
            "pkgset_name",
            "rs_pkgset_name_bugzilla",
            "rs_start_date",
            "rs_end_date",
            "rs_show",
            "rs_description_ru",
            "rs_description_en",
            "rs_mailing_list",
            "rs_mirrors_json",
        ]

        for elem in self.args["json_data"]["branches"]:
            # Convert string pkgset_name to lowercase
            elem["pkgset_name"] = elem["pkgset_name"].lower()

            # decode base64
            try:
                elem["rs_description_ru"] = base64.b64decode(elem["rs_description_ru"])
                elem["rs_description_en"] = base64.b64decode(elem["rs_description_en"])
            except binascii.Error:
                self.validation_results.append("description must be in base64 format")

            if elem["rs_description_ru"] == "" or elem["rs_description_en"] == "":
                self.validation_results.append("description cannot be misleading")

            if elem["rs_show"] > 1 or elem["rs_show"] < 0:
                self.validation_results.append("allowable values rs_show : 0 or 1")

            for key in elem.keys():
                self.input_params.append(key)

        if set(self.input_params) != set(self.known_param):
            self.validation_results.append(f"allowable values : {self.known_param}")

        if self.validation_results != []:
            return False
        else:
            return True

    def post(self):
        """
        Load repository data
        """
        json_ = self.args["json_data"]["branches"]

        for el in json_:
            el["rs_start_date"] = dt.datetime.fromisoformat(el["rs_start_date"])
            el["rs_end_date"] = dt.datetime.fromisoformat(el["rs_end_date"])
            el["rs_mirrors_json"] = json.dumps(el["rs_mirrors_json"], default=str)

        self.conn.request_line = (self.sql.insert_pkgset_status, json_)
        status, response = self.conn.send_request()

        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        return "data loaded successfully", 201

    def get(self):
        """
        Get information about a repository
        """
        self.conn.request_line = self.sql.get_pkgset_status

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

        RepositoryStatusInfo = namedtuple(
            "RepositoryStatusInfo",
            [
                "branch",
                "pkgset_name_bugzilla",
                "start_date",
                "end_date",
                "show",
                "description_ru",
                "description_en",
                "url_mailing_list",
                "mirrors_json"
            ],
        )

        res = [RepositoryStatusInfo(*el)._asdict() for el in response]
        for el in res:
            el["mirrors_json"] = json.loads(el["mirrors_json"])
        res = {"branches": res}

        return res, 200


class ActivePackagesets(APIWorker):
    """Retrieves list of active package sets."""

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def get(self):
        self.conn.request_line = self.sql.get_active_pkgsets
        status, response = self.conn.send_request()

        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error

        if not response:
            self.logger.debug(f"No active package sets found in DB")
            res = {"packagesets": sort_branches(lut.known_branches)}
        else:
            res = {"packagesets": sort_branches([el[0] for el in response])}

        res["length"] = len(res["packagesets"])  # type: ignore

        return res, 200
