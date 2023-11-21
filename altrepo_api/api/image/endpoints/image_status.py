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

import base64
import binascii
import datetime as dt
import json
from collections import namedtuple

from altrepo_api.api.base import APIWorker
from altrepo_api.utils import sort_branches
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
            self.payload["img_description_ru"] = base64.b64decode(
                self.payload["img_description_ru"]
            )
            self.payload["img_description_en"] = base64.b64decode(
                self.payload["img_description_en"]
            )
        except binascii.Error:
            self.validation_results.append("description must be in base64 format")

        if (
            self.payload["img_description_ru"] == ""
            or self.payload["img_description_en"] == ""
        ):
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
                "summary_ru",
                "summary_en",
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
                summary_ru=p["img_summary_ru"],
                summary_en=p["img_summary_en"],
                description_ru=description_ru,
                description_en=description_en,
                mailing_list=p["img_mailing_list"],
                name_bugzilla=p["img_name_bugzilla"],
                json=json.dumps(p["img_json"], default=str),
            )

        images = [img2ntuple(p) for p in self.payload["images"]]

        _ = self.send_sql_request((self.sql.insert_image_status, images))
        if not self.sql_status:
            return self.error

        return "data loaded successfully", 201

    def get(self):
        """
        Get information about a image
        """

        response = self.send_sql_request(self.sql.get_img_status)
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {"message": "No data not found in database", "args": self.args}
            )

        ImageStatusInfo = namedtuple(
            "RepositoryStatusInfo",
            [
                "branch",
                "edition",
                "name",
                "show",
                "summary_ru",
                "summary_en",
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


class ImageTagStatus(APIWorker):
    """
    Upload or get information on current iso images.
    """

    def __init__(self, connection, payload, **kwargs):
        self.conn = connection
        self.payload = payload
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def check_params_get(self):
        self.logger.debug(f"args : {self.args}")
        self.validation_results = []

        if self.args["branch"] not in lut.known_branches:
            self.validation_results.append(
                f"unknown package set name : {self.args['branch']}"
            )
            self.validation_results.append(
                f"allowed package set names are : {lut.known_branches}"
            )

        if self.validation_results != []:
            return False
        else:
            return True

    def post(self):
        """
        Load iso image data
        """

        Tags = namedtuple("Tags", ["tag", "show"])

        def img2ntuple(p: dict) -> Tags:
            return Tags(tag=p["img_tag"], show=p["img_show"])

        images = [img2ntuple(p) for p in self.payload["tags"]]
        _ = self.send_sql_request((self.sql.insert_image_tag_status, images))
        if not self.sql_status:
            return self.error

        return "data loaded successfully", 201

    def get(self):
        """
        Get information about a iso image
        """
        branch = self.args["branch"]
        if self.args["edition"] is not None:
            edition = f"AND img_edition = '{self.args['edition']}'"
        else:
            edition = ""

        response = self.send_sql_request(
            self.sql.get_img_tag_status.format(branch=branch, edition=edition)
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {"message": "No data not found in database", "args": self.args}
            )

        ImageTagStatusInfo = namedtuple("ImageTagStatusInfo", ["tag", "show"])

        res = [ImageTagStatusInfo(*el)._asdict() for el in response]
        res = {"tags": res}

        return res, 200


class ActiveImages(APIWorker):
    """
    Get information on active images.
    """

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def check_params_get(self):
        self.logger.debug(f"args : {self.args}")
        self.validation_results = []

        if self.args["branch"] not in lut.known_branches:
            self.validation_results.append(
                f"unknown package set name : {self.args['branch']}"
            )
            self.validation_results.append(
                f"allowed package set names are : {lut.known_branches}"
            )

        if self.validation_results != []:
            return False
        else:
            return True

    def _parse_version(self, version: str) -> tuple[int, int, int]:
        try:
            major_ = minor_ = sub_ = 0
            s = version.strip().split(".")
            major_ = int(s[0])

            if len(s) >= 2:
                minor_ = int(s[1])
            if len(s) == 3:
                sub_ = int(s[2])
            if len(s) > 3:
                raise ValueError

            return major_, minor_, sub_
        except ValueError:
            msg = "Failed to parse version: '{0}'.".format(version)
            raise ValueError(msg)

    def get(self):
        branch = self.args["branch"]
        edition = self.args["edition"]
        version = self.args["version"]
        release = self.args["release"]
        variant = self.args["variant"]
        img_type = self.args["type"]

        image_clause = f" AND img_branch = '{branch}'"

        if edition:
            image_clause += f" AND img_edition = '{edition}'"
        if version:
            v = self._parse_version(version)
            image_clause += (
                f" AND (img_version_major, img_version_minor, img_version_sub) = {v}"
            )
        if release:
            image_clause += f" AND img_release = '{release}'"
        if variant:
            image_clause += f" AND img_variant = '{variant}'"
        if img_type:
            image_clause += f" AND img_type = '{img_type}'"

        response = self.send_sql_request(
            self.sql.get_active_images.format(image_clause=image_clause, branch=branch)
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {"message": "No data not found in database", "args": self.args}
            )

        ActiveImagesInfo = namedtuple(
            "ActiveImagesInfo",
            ["edition", "tags"],
        )

        res = [ActiveImagesInfo(*el)._asdict() for el in response]

        res = {"request_args": self.args, "length": len(res), "images": res}
        return res, 200


class ImagePackageSet(APIWorker):
    """
    Get a list of package sets which has an active images.
    """

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def check_params(self):
        return True

    def get(self):
        response = self.send_sql_request(self.sql.get_img_pkgset)
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {"message": "No data not found in database", "args": self.args}
            )

        branches = sort_branches(response[0][0])

        res = {"length": len(branches), "branches": list(branches)}

        return res, 200
