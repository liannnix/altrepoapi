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

from uuid import UUID
from collections import namedtuple

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
        self.conn.request_line = self.sql.get_all_iso_images
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

        ImageInfo = namedtuple(
            "ImageInfo", ["branch", "name", "tag", "file", "uuid", "date"]
        )
        images = [ImageInfo(*r)._asdict() for r in response]

        res = {"length": len(images), "images": images}
        return res, 200


class ISOImageInfo(APIWorker):
    """Retrieves ISO images info from DB."""

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

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

        return tuple()

    def get(self):
        # get ISO images info
        arch = self.args["arch"]
        branch = self.args["branch"]
        edition = self.args["edition"]
        version = self.args["version"]
        release = self.args["release"]
        variant = self.args["variant"]
        component = self.args["component"]

        image_clause = f" AND img_branch = '{branch}'"

        if arch:
            image_clause += f" AND img_arch = '{arch}'"
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

        # get iso roots info
        self.conn.request_line = self.sql.get_iso_root_info.format(
            image_clause=image_clause
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

        ImageRaw = namedtuple(
            "ImageRaw",
            [
                "uuid",
                "date",
                "tag",
                "branch",
                "edition",
                "flavor",
                "platform",
                "release",
                "version_major",
                "version_minor",
                "version_sub",
                "arch",
                "variant",
                "type",
                "kv",
            ],
        )
        images: dict[UUID, ImageRaw] = {r[0]: ImageRaw(*r) for r in response}  # type: ignore
        ruuids = [str(i.uuid) for i in images.values()]

        # get components info
        component_clause = ""
        if component is not None and component != "iso":
            component_clause = f" AND pkgset_nodename = '{component}'"

        self.conn.request_line = self.sql.get_iso_image_components.format(
            ruuids=ruuids, component_clause=component_clause
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

        Component = namedtuple("Component", ["ruuid", "uuid", "name", "kv"])

        def _process_components(comps: list[Component]) -> list[dict]:
            res = []
            for c in comps:
                d = c._asdict()
                if c.name == "iso":
                    d["image_size"] = bytes2human(int(c.kv["size"]))
                    d["pkg_count"] = 0
                elif "image_size" in c.kv:
                    d["image_size"] = bytes2human(int(c.kv["image_size"]))
                    d["pkg_count"] = int(c.kv["size"])
                else:
                    d["image_size"] = ""
                    d["pkg_count"] = int(c.kv["size"])
                res.append(d)
            return res

        # build 'iso' component from ISO root info
        isos: dict[UUID, list[Component]] = {}
        for uuid, i in images.items():
            isos[uuid] = []
            isos[uuid].append(Component(ruuid=i.uuid, uuid=i.uuid, name="iso", kv=i.kv))

        for comp in [Component(*r) for r in response]:
            isos[comp.ruuid].append(comp)

        def make_download_mirrors(url: str) -> list[str]:
            # build mirror.yandex.ru alternative download links
            res = [url,]
            if (
                url.startswith("http://ftp.altlinux.org/pub/distributions/ALTLinux/images")
            ):
                res.append(
                    url.replace(
                    "http://ftp.altlinux.org/pub/distributions/ALTLinux/images",
                    "https://mirror.yandex.ru/altlinux/images/"
                    )
                )

            return res

        res: list[dict] = []
        for ruuid in isos:
            image = images[ruuid]._asdict()
            image["file"] = image["kv"]["file"]
            image["url"] = make_download_mirrors(image["kv"]["url"])
            image["md5sum"] = image["kv"]["md5_cs"]
            image["gost12sum"] = image["kv"]["gost12_cs"]
            image["sha256sum"] = image["kv"]["sha256_cs"]
            del image["kv"]

            if component is not None:
                components = _process_components(
                    [c for c in isos[ruuid] if c.name == component]
                )
            else:
                components = _process_components(isos[ruuid])
            if not components:
                continue
            image["components"] = components
            res.append(image)

        res.sort(key=lambda x: (x["date"], x["tag"]), reverse=True)

        return {"request_args": self.args, "length": len(res), "images": res}, 200
