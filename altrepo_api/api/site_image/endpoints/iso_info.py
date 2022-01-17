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

import json
import datetime
from collections import namedtuple
from dataclasses import dataclass, asdict
from uuid import UUID
from typing import Any

from altrepo_api.utils import bytes2human
from altrepo_api.api.base import APIWorker
from ..sql import sql


class AllISOImages(APIWorker):
    """Retrieves ISO images list."""

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def get(self):
        self.conn.request_line = self.sql.get_all_iso_names
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

        iso = [
            {"uuid": x[0], "name": x[1], "date": x[2]}
            for x in sorted(response, key=lambda x: x[1])
            if len(x) == 3
        ]

        res = {"length": len(iso), "images": iso}
        return res, 200


_ImageRaw = namedtuple(
    "_ImageRaw", ["ruuid", "rname", "date", "depth", "uuid", "name", "k", "v"]
)


@dataclass
class ImageInfo:
    iso_uuid: UUID
    iso_name: str
    iso_date: datetime.datetime
    uuid: UUID
    depth: int
    date: datetime.datetime
    json: dict[str, Any]
    type_: str = ""
    class_: str = ""
    name: str = ""
    size: int = 0
    size_readable: str = "0"


class ISOImageInfo(APIWorker):
    """Retrieves ISO images info from DB."""

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def _process_image_info(self, img: _ImageRaw) -> ImageInfo:
        # unpack image record
        res = ImageInfo(
            iso_uuid=img.ruuid,
            iso_name=img.rname,
            iso_date=img.date,
            uuid=img.uuid,
            depth=img.depth,
            date=img.date,
            name=img.name,
            json={},
        )

        t = {k: v for k, v in zip(img.k, img.v)}

        type_ = t.get("type", "unknown")
        if type_ not in ("iso", "rpms", "squashfs"):
            raise ValueError(f"Unsupported image type: {type_}")
        # process 'kv' dictionary
        if type_ == "iso":
            res.type_ = "iso"
            res.name = "iso"
            res.class_ = "iso"
            res.size = int(t["size"])
            res.size_readable = bytes2human(int(t["size"]))
            res.date = datetime.datetime.strptime(t["date"], "%Y%m%d")
            res.json = json.loads(t["json"])
            res.json["info"] = t["info"]
            res.json["isoinfo"] = t["isoinfo"]
            res.json["commit"] = t["commit"].split("\n")
        elif type_ == "rpms":
            res.type_ = t["type"]
            res.class_ = "iso"
            res.size = int(t["size"])
            res.size_readable = f'{t["size"]} packages'
            res.date = res.iso_date
        elif type_ == "squashfs":
            res.type_ = t["type"]
            res.class_ = "iso"
            res.size = int(t["image_size"])
            res.size_readable = bytes2human(int(t["image_size"]))
            res.date = datetime.datetime.fromisoformat(t["mtime"])
            res.json["packages"] = int(t["size"])
            res.json["orphaned_files"] = int(t["orphaned_files"])
            res.json["hash"] = t["hash"]
            res.json["sha1"] = t["sha1"]

        return res

    def get(self):
        # get ISO images info
        arch = self.args["arch"]
        branch = self.args["branch"]
        edition = self.args["edition"]
        version = self.args["version"]
        release = self.args["release"]
        variant = self.args["variant"]
        component = self.args["component"]

        image_clause = f" AND startsWith(pkgset_name, '{branch}:')"

        if arch:
            image_clause += f" AND position(pkgset_name, ':{arch}:') != 0"
        if edition:
            image_clause += f" AND position(pkgset_name, ':{edition}:') != 0"
        if version:
            image_clause += f" AND position(pkgset_name, '.{version}:') != 0"
        if release:
            image_clause += f" AND position(pkgset_name, ':{release}.') != 0"
        if variant:
            image_clause += f" AND position(pkgset_name, ':{variant}:') != 0"

        component_clause = ""
        if component:
            if component == "iso":
                component_clause = f" AND pkgset_depth = 0"
            else:
                component_clause = f" AND pkgset_nodename = '{component}'"

        self.conn.request_line = self.sql.get_all_iso_info.format(
            image_clause=image_clause, component_clause=component_clause
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

        images: list[ImageInfo] = [
            self._process_image_info(_ImageRaw(*r)) for r in response
        ]

        res = {}
        for img in sorted(images, key=lambda x: (x.iso_name, x.depth)):
            ruuid = str(img.iso_uuid)
            if ruuid not in res:
                res[ruuid] = {
                    "name": img.iso_name,
                    "date": img.iso_date,
                    "uuid": img.iso_uuid,
                    "components": [],
                }
            res[ruuid]["components"].append(asdict(img))

        res = [v for v in res.values()]

        return {"length": len(res), "images": res}, 200
