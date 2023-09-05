# ALTRepo API
# Copyright (C) 2023  BaseALT Ltd

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

import re
import copy

from collections import defaultdict
from datetime import datetime
from typing import NamedTuple, Union
from itertools import chain

from altrepo_api.api.base import APIWorker
from altrepo_api.api.misc import lut
from altrepo_api.utils import mmhash
from ..sql import sql


PARTIAL_IMAGE_VERSION = re.compile(r"^(\d+)+\.{,1}(\d+)*\.{,1}(\d+)*$")


FILTER_FIELDS = {
    "editions": {
        "validator": lambda x: [e for e in x if e not in lut.known_image_editions],
        "valid_values": ", ".join(f"'{e}'" for e in lut.known_image_editions),
    },
    "releases": {
        "validator": lambda x: [e for e in x if e not in lut.known_image_releases],
        "valid_values": ", ".join(f"'{e}'" for e in lut.known_image_releases),
    },
    "versions": {
        "validator": lambda x: [e for e in x if not PARTIAL_IMAGE_VERSION.search(e)],
        "valid_values": "dot-separated strings of positive integers without spaces",
    },
    "archs": {
        "validator": lambda x: [e for e in x if e not in lut.known_image_archs],
        "valid_values": ", ".join(f"'{e}'" for e in lut.known_image_archs),
    },
    "types": {
        "validator": lambda x: [e for e in x if e not in lut.known_image_types],
        "valid_values": ", ".join(f"'{e}'" for e in lut.known_image_types),
    },
    "variants": {
        "validator": lambda x: [e for e in x if e not in lut.known_image_variants],
        "valid_values": ", ".join(f"'{e}'" for e in lut.known_image_variants),
    },
}


def make_tagpatterns(branch: str, filters: list[dict[str, list[str]]]) -> list[str]:
    filters = copy.deepcopy(filters)
    fields = [
        "branch",
        "edition",
        "flavor",
        "platform",
        "release",
        "version",
        "arch",
        "variant",
        "type",
    ]

    # normalize images versions
    # 10   -> 10\..*\..*
    # 10.1 -> 10\.1\..*
    for f in filters:
        if "versions" in f:
            f["versions"] = [
                r"\.".join(
                    [str(maybe) if maybe else ".*" for maybe in parse_image_version(v)]
                )
                for v in f["versions"]
            ]

    def regex_alternatives(alternatives: list) -> str:
        return ("(%s){1}" % "|".join(map(str, alternatives))) if alternatives else ".*"

    def parts(filter: dict) -> list[str]:
        return [regex_alternatives(filter.get(field + "s", [])) for field in fields]

    def tag(fields: list[str]) -> str:
        return ":".join(chain(fields[:4], [r"\.".join(fields[4:6])], fields[6:]))

    result = [tag(parts(filter | {"branchs": [branch]})) for filter in filters]

    return result if result else [tag(parts({"branchs": [branch]}))]


def parse_image_version(version: str) -> tuple[int, Union[int, None], Union[int, None]]:
    parsed = PARTIAL_IMAGE_VERSION.search(version)
    if not parsed:
        raise ValueError("Failed to parse version: '{0}'.".format(version))
    return tuple(int(el) if el else el for el in parsed.groups())  # type: ignore


class CheckImages(APIWorker):
    """
    Determine images which use binary packages from specified task.
    Allowed task's states: EPERM, TESTED or DONE.
    Listed only active images for task's branch.
    """

    def __init__(self, connection, **kwargs) -> None:
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def check_params(self):
        json_data = self.args["json_data"]

        try:
            task_id = int(json_data["task_id"])
        except KeyError:
            self.validation_results.append("task_id is required")
            return False

        response = self.send_sql_request(self.sql.check_task.format(id=task_id))
        if not self.sql_status:
            return False
        if not (response[0][0] != 0):
            self.validation_results.append(f"Task not found: {task_id}")
            return False

        if "filters" in json_data:
            for index, filter in enumerate(json_data["filters"]):
                for filter_name, filter_value in filter.items():
                    if filter_name not in FILTER_FIELDS:
                        self.validation_results.append(
                            f"Filter #{index}: unknown filter: '{filter_name}'"
                        )
                        continue

                    validator = FILTER_FIELDS[filter_name]["validator"]
                    valid_values = FILTER_FIELDS[filter_name]["valid_values"]

                    invalids = validator(filter_value)
                    if invalids:
                        for invalid in invalids:
                            self.validation_results.append(
                                f"Filter #{index}: invalid value '{invalid}' for "
                                f"field '{filter_name}'; "
                                f"valid values are: {valid_values}"
                            )
                        continue

        if self.validation_results != []:
            return False

        return True

    def post(self):
        class TaskInfo(NamedTuple):
            task_id: int
            task_state: str
            task_changed: datetime
            task_try: int
            task_iter: int
            task_repo: str

        class PackageInfo(NamedTuple):
            from_subtask: int
            status: str
            srcpkg_name: str
            binpkg_name: str
            binpkg_arch: str

        class ImageInfo(NamedTuple):
            branch: str
            edition: str
            flavor: str
            platform: str
            release: str
            major_version: str
            minor_version: str
            sub_version: str
            arch: str
            variant: str
            type: str
            file: str
            buildtime: datetime

        json_data = self.args["json_data"]
        task_id = json_data["task_id"]
        packages_names = set(json_data.get("packages_names", []))
        filters = json_data.get("filters", [])

        response = self.send_sql_request(
            self.sql.get_last_task_info.format(task_id=task_id)
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {"Error": (f"No data found in database for task '{task_id}'")}
            )

        task = TaskInfo(*response[0][:2], *response[0][5:-1])

        if task.task_state not in ("TESTED", "DONE", "EPERM"):
            return self.store_error(
                {
                    "Error": f"Task '{task.task_id}' isn't in state TESTED, "
                    "DONE or EPERM"
                }
            )

        task_plan_hashes = [
            mmhash(f"{task.task_id}{task.task_try}{task.task_iter}{arch}")
            for arch in lut.default_archs + ["x86_64-i586"]
        ]

        _packages_tmp_table = "packages_tmp_table"
        response = self.send_sql_request(
            self.sql.prepare_packages_temporary_table.format(
                tmp_table=_packages_tmp_table,
                task_id=task.task_id,
                task_changed=task.task_changed,
                tplan_hashes=task_plan_hashes,
            )
        )
        if not self.sql_status:
            return self.error

        _tagpatterns_tmp_table = "tagpatterns_tmp_table"

        response = self.send_sql_request(
            self.sql.get_packages_in_images.format(
                tagpatterns_tmp_table=_tagpatterns_tmp_table,
                packages_tmp_table=_packages_tmp_table,
            ),
            external_tables=[
                {
                    "name": _tagpatterns_tmp_table,
                    "structure": [
                        ("tagpattern", "String"),
                    ],
                    "data": [
                        {"tagpattern": tp}
                        for tp in make_tagpatterns(task.task_repo, filters)
                    ],
                }
            ],
        )
        if not self.sql_status:
            return self.error

        in_images: dict[ImageInfo, list[PackageInfo]] = defaultdict(list)
        not_in_images: list[PackageInfo] = []

        if packages_names:
            for row in response:
                i = ImageInfo(*row[:13])
                p = PackageInfo(*row[13:])

                if p.binpkg_name in packages_names:
                    if not i.file:
                        not_in_images.append(p)
                        continue
                    in_images[i].append(p)
        else:
            for row in response:
                i = ImageInfo(*row[:13])
                p = PackageInfo(*row[13:])

                if not i.file:
                    not_in_images.append(p)
                    continue
                in_images[i].append(p)

        return {
            "request_args": self.args,
            "in_images": sorted(
                (
                    img._asdict()
                    | {
                        "packages": sorted(
                            (p._asdict() for p in packages),
                            key=lambda e: (e["srcpkg_name"], e["binpkg_name"]),
                        )
                    }
                    for img, packages in in_images.items()
                ),
                key=lambda e: e["file"],
            ),
            "not_in_images": sorted(
                (p._asdict() for p in not_in_images),
                key=lambda e: (e["srcpkg_name"], e["binpkg_name"]),
            ),
        }, 200
