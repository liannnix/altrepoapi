# ALTRepo API
# Copyright (C) 2021-2022  BaseALT Ltd

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

from altrepo_api.api.base import APIWorker
from ..sql import sql
from ...misc import lut


class ImageStatus(APIWorker):
    """
    Upload or get information on current images.
    """

    def __init__(self, connection, payload, **kwargs):
        self.conn = connection
        self.payload = payload
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def check_params_post(self):
        self.logger.debug(f"args : {self.args}")
        self.validation_results = []

        if self.payload["img_branch"] not in lut.known_branches:
            self.validation_results.append(
                f"unknown package set name : {self.payload['img_branch']}"
            )
            self.validation_results.append(
                f"allowed package set names are : {lut.known_branches}"
            )

        # decode base64
        try:
            self.payload["img_description_ru"] = base64.b64decode(self.payload["img_description_ru"])
            self.payload["img_description_en"] = base64.b64decode(self.payload["img_description_en"])
        except binascii.Error:
            self.validation_results.append("description must be in base64 format")

        if self.payload["img_description_ru"] == "" or self.payload["img_description_en"] == "":
            self.validation_results.append("description cannot be misleading")

        if self.validation_results != []:
            return False
        else:
            return True

    def post(self):
        """
        Load image data
        """
        branch = self.payload["img_branch"]
        description_ru = self.payload["img_description_ru"]
        description_en = self.payload["img_description_en"]

        Image = namedtuple(
            "Image",
            [
                "branch",
                "edition",
                "name",
                "show",
                "start_date",
                "end_date",
                "description_ru",
                "description_en",
                "mailing_list",
                "name_bugzilla",
                "json",
            ],
        )

        def img2ntuple(p: dict) -> Image:
            return Image(
                branch=branch,
                edition=p["img_edition"],
                name=p["img_name"],
                show=p["img_show"],
                start_date=dt.datetime.fromisoformat(p["img_start_date"]),
                end_date=dt.datetime.fromisoformat(p["img_end_date"]),
                description_ru=description_ru,
                description_en=description_en,
                mailing_list=p["img_mailing_list"],
                name_bugzilla=p["img_name_bugzilla"],
                json=json.dumps(p["img_json"], default=str),
            )

        images = [img2ntuple(p) for p in self.payload["images"]]
        self.conn.request_line = (self.sql.insert_image_status, images)
        status, response = self.conn.send_request()

        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        return "data loaded successfully", 201

    def get(self):
        """
        Get information about a image
        """
        self.conn.request_line = self.sql.get_img_status

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

        ImageStatusInfo = namedtuple(
            "RepositoryStatusInfo",
            [
                "edition",
                "branch",
                "name",
                "show",
                "start_date",
                "end_date",
                "description_ru",
                "description_en",
                "mailing_list",
                "name_bugzilla",
                "json",
            ],
        )

        res = [ImageStatusInfo(*el)._asdict() for el in response]
        for el in res:
            el["json"] = json.loads(el["json"])
        res = {"images": res}

        return res, 200
