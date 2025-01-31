# ALTRepo API
# Copyright (C) 2021-2025  BaseALT Ltd

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

from altrepo_api.utils import bytes2human, make_tmp_table_name
from altrepo_api.api.base import APIWorker
from ..sql import sql
from ...misc import lut


MAX_LIMIT = 10_000


class AllISOImages(APIWorker):
    """Retrieves ISO images list."""

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def get(self):
        response = self.send_sql_request(self.sql.get_all_iso_images)
        if not self.sql_status:
            return self.error
        if not response:
            self.store_error(
                {"message": "No data not found in database", "args": self.args}
            )

        ImageInfo = namedtuple(
            "ImageInfo", ["branch", "name", "tag", "file", "uuid", "date"]
        )

        images = [ImageInfo(*r)._asdict() for r in response]  # type: ignore

        res = {"length": len(images), "images": images}

        return res, 200


class ImageInfo(APIWorker):
    """Retrieves images info from DB."""

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
        flavor = self.args["flavor"]
        platform = self.args["platform"]
        img_type = self.args["type"]

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
        if flavor:
            image_clause += f" AND img_flavor = '{flavor}'"
        if platform:
            image_clause += f" AND img_platform = '{platform}'"
        if img_type:
            image_clause += f" AND img_type = '{img_type}'"

        # get iso roots info
        response = self.send_sql_request(
            self.sql.get_img_root_info.format(image_clause=image_clause)
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {"message": "No data not found in database", "args": self.args}
            )

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
        response = self.send_sql_request(
            self.sql.get_iso_image_components.format(ruuids=ruuids)
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {"message": "No data not found in database", "args": self.args}
            )

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
                elif "size" in c.kv and c.name in ("tar", "img", "qcow"):
                    d["image_size"] = bytes2human(int(c.kv["size"]))
                    d["pkg_count"] = 0
                else:
                    d["image_size"] = ""
                    d["pkg_count"] = int(c.kv["size"])
                res.append(d)
            return res

        # build root component from image root info
        image_components: dict[UUID, list[Component]] = {}
        for uuid, i in images.items():
            image_components[uuid] = []
            image_components[uuid].append(
                Component(ruuid=i.uuid, uuid=i.uuid, name=i.kv["class"], kv=i.kv)
            )

        for comp in [Component(*r) for r in response]:  # type: ignore
            image_components[comp.ruuid].append(comp)

        def make_download_mirrors(url: str) -> list[str]:
            # build mirror.yandex.ru alternative download links
            res = [
                url,
            ]
            if url.startswith(
                "http://ftp.altlinux.org/pub/distributions/ALTLinux/images"
            ):
                res.append(
                    url.replace(
                        "http://ftp.altlinux.org/pub/distributions/ALTLinux/images",
                        "https://mirror.yandex.ru/altlinux/images/",
                    )
                )

            return res

        res: list[dict] = []
        for ruuid in image_components:
            image = images[ruuid]._asdict()
            image["file"] = image["kv"]["file"]
            image["url"] = make_download_mirrors(image["kv"]["url"])
            image["md5sum"] = image["kv"]["md5_cs"]
            image["gost12sum"] = image["kv"]["gost12_cs"]
            image["sha256sum"] = image["kv"]["sha256_cs"]
            del image["kv"]

            if component is not None:
                components = _process_components(
                    [c for c in image_components[ruuid] if c.name == component]
                )
            else:
                components = _process_components(image_components[ruuid])
            if not components:
                continue
            image["components"] = components
            res.append(image)

        res.sort(key=lambda x: (x["date"], x["tag"]), reverse=True)

        return {"request_args": self.args, "length": len(res), "images": res}, 200


class LastImagePackages(APIWorker):
    def __init__(self, connection, is_cve=False, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.is_cve = is_cve
        self.sql = sql
        super().__init__()

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        self.validation_results = []

        limit = self.args["packages_limit"]
        if limit and (limit < 1 or limit > MAX_LIMIT):
            self.validation_results.append(
                f"last packages limit should be in range 1 to {MAX_LIMIT}"
            )

        return self.validation_results == []

    def get(self):
        uuid = self.args["uuid"]
        branch = self.args["branch"]
        packages_limit = self.args["packages_limit"]
        component = self.args["component"]

        if packages_limit:
            limit = f"LIMIT {packages_limit}"
        else:
            limit = ""

        if self.is_cve:
            cve = r"AND match(chlog_text, 'CVE-\d{4}-(\d{7}|\d{6}|\d{5}|\d{4})')"
        else:
            cve = ""

        tmp_pkg_hashes = make_tmp_table_name("pkg_hashes")
        if component is not None:
            component = f"AND pkgset_nodename = '{component}'"
        else:
            component = ""

        _ = self.send_sql_request(
            self.sql.tmp_last_image_cmp_pkg_diff.format(
                tmp_table=tmp_pkg_hashes, uuid=uuid, component=component
            )
        )
        if not self.sql_status:
            return self.error

        tmp_table = make_tmp_table_name("img_pkg_info")
        _ = self.send_sql_request(
            self.sql.tmp_img_pkg_info.format(
                tmp_table=tmp_table, tmp_pkg_hashes=tmp_pkg_hashes
            )
        )
        if not self.sql_status:
            return self.error

        response = self.send_sql_request(
            self.sql.get_last_image_pkgs_info.format(
                tmp_table=tmp_table, branch=branch, cve=cve, limit=limit
            )
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {
                    "message": "No data found in database for packages",
                    "args": self.args,
                }
            )

        PkgMeta = namedtuple(
            "PkgMeta",
            [
                "task_id",
                "task_changed",
                "tplan_action",
                "branch",
                "pkg_hash",
                "pkg_name",
                "pkg_version",
                "pkg_release",
                "pkg_arch",
                "chlog_date",
                "chlog_name",
                "chlog_nick",
                "chlog_evr",
                "chlog_text",
                "img_pkg_hash",
                "pkg_summary",
                "img_pkg_version",
                "img_pkg_release",
            ],
        )

        packages = [PkgMeta(*el)._asdict() for el in response]  # type: ignore

        res = {
            "request_args": self.args,
            "length": len(packages),
            "packages": packages,
        }
        return res, 200


class ImageTagUUID(APIWorker):
    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def get(self):
        img_tag = self.args["tag"]

        response = self.send_sql_request(
            self.sql.get_image_uuid_by_tag.format(img_tag=img_tag)
        )
        if not self.sql_status:
            return self.error

        if (
            not response
            or str(response[0][0]) == "00000000-0000-0000-0000-000000000000"  # type: ignore
        ):
            return self.store_error(
                {
                    "message": f"Image tag '{img_tag}' not found.",
                    "args": self.args,
                }
            )

        ImgInfo = namedtuple(
            "ImgInfo",
            [
                "uuid",
                "components",
                "file",
                "type",
            ],
        )

        img_info = ImgInfo(*response[0])  # type: ignore
        res = {
            "request_args": self.args,
            "uuid": img_info.uuid,
            "file": img_info.file,
            "type": img_info.type,
            "components": img_info.components,
        }
        return res, 200


class ImageCategoriesCount(APIWorker):
    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def get(self):
        uuid = self.args["uuid"]
        component = self.args["component"]

        component_clause = ""
        if component:
            component_clause += f"AND pkgset_nodename = '{component}'"

        response = self.send_sql_request(
            self.sql.get_image_groups_count.format(
                uuid=uuid, component=component_clause
            )
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {"message": "No data not found in database", "args": self.args}
            )

        res = [{"category": el[0], "count": el[1]} for el in response]

        res = {"request_args": self.args, "length": len(res), "categories": res}
        return res, 200


class ImagePackages(APIWorker):
    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        self.validation_results = []

        if self.args["group"]:
            match = False
            if self.args["group"] not in lut.pkg_groups:
                for el in lut.pkg_groups:
                    if (
                        el.startswith(self.args["group"])
                        and self.args["group"][-1] == "/"
                    ) or el.startswith(self.args["group"] + "/"):
                        match = True
                        break
            else:
                match = True
            if not match:
                self.validation_results.append(
                    f"unknown package category : {self.args['group']}"
                )
                self.validation_results.append(
                    f"allowed package categories : {lut.pkg_groups}"
                )

        if self.validation_results != []:
            return False
        else:
            return True

    def get(self):
        group = self.args["group"]
        uuid = self.args["uuid"]
        component = self.args["component"]

        if group is not None:
            group_clause = f"AND pkg_group_ LIKE '{group}%%'"
        else:
            group_clause = ""

        if component is not None:
            component = f"AND pkgset_nodename = '{component}'"
        else:
            component = ""

        response = self.send_sql_request(
            self.sql.get_image_packages.format(
                uuid=uuid, group=group_clause, component=component
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

        PkgMeta = namedtuple(
            "PkgMeta",
            [
                "hash",
                "pkg_name",
                "pkg_version",
                "pkg_release",
                "pkg_arch",
                "pkg_summary",
                "pkg_buildtime",
                "changelog_date",
                "changelog_name",
                "changelog_evr",
                "changelog_text",
            ],
        )

        retval = [PkgMeta(*el)._asdict() for el in response]

        subcategories = []
        response = self.send_sql_request(
            self.sql.get_group_subgroups.format(
                uuid=uuid, group=group, component=component
            )
        )
        if not self.sql_status:
            return self.error

        if response:
            subcategories = [el[0] for el in response]

        res = {
            "request_args": self.args,
            "length": len(retval),
            "subcategories": subcategories,
            "packages": retval,
        }
        return res, 200
