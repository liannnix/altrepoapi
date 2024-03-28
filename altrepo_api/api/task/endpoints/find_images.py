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

from collections import defaultdict
from datetime import datetime
from typing import Any, NamedTuple

from altrepo_api.utils import valid_task_id
from altrepo_api.api.base import APIWorker

from ..sql import sql


class FindImages(APIWorker):
    """
    Find images which contain binary packages with the same names as binaries
    from a task. A task should be in the one of the following states:
    EPERM, TESTED or DONE
    """

    def __init__(self, connection, id_, **kwargs) -> None:
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        self.task_id = id_
        super().__init__()

    def check_task_id(self):
        if not valid_task_id(self.task_id):
            return False
        response = self.send_sql_request(self.sql.check_task.format(id=self.task_id))
        if not self.sql_status:
            return False

        return response[0][0] != 0

    def get(self):
        class Subtask(NamedTuple):
            id: int
            type: str
            srpm_name: str
            srpm_hash: str
            pkg_version: str
            pkg_release: str

        class SubtaskWithBinary(NamedTuple):
            id: int
            type: str
            srpm_name: str
            srpm_hash: str
            pkg_version: str
            pkg_release: str
            binpkg_name: str
            binpkg_arch: str

        class Image(NamedTuple):
            filename: str
            edition: str
            tag: str
            buildtime: datetime
            binpkg_name: str
            binpkg_version: str
            binpkg_release: str
            binpkg_arch: str
            binpkg_hash: str

        def inner_join(
            packages: list[SubtaskWithBinary],
            images: list[Image],
        ) -> list[tuple[SubtaskWithBinary, Image]]:
            return [
                (package, image)
                for image in images
                for package in packages
                if (
                    (package.binpkg_name, package.binpkg_arch)
                    == (image.binpkg_name, image.binpkg_arch)
                )
            ]

        task: dict[str, Any] = {}
        task["task_id"] = self.task_id

        response = self.send_sql_request(
            self.sql.get_last_task_info.format(task_id=self.task_id)
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {"Error": f"No data found in database for task '{self.task_id}'"}
            )

        (
            task["task_state"],
            task["dependencies"],
            task["task_testonly"],
            task["task_message"],
            task["task_changed"],
            task["task_try"],
            task["task_iter"],
            task["task_repo"],
            task["task_owner"],
        ) = response[0][1:]

        if task["task_state"] not in ("TESTED", "DONE", "EPERM"):
            return self.store_error(
                {"Error": f"Task '{self.task_id}' isn't in state TESTED, DONE or EPERM"}
            )

        response = self.send_sql_request(
            self.sql.get_task_iterations.format(task_id=self.task_id)
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {"message": "No data not found in database"},
            )

        task["iterations"] = sorted(
            [{"task_try": r[0], "task_iter": r[1]} for r in response[0][0]],
            key=lambda el: (el["task_try"], el["task_iter"]),
            reverse=True,
        )

        archs = ("noarch", "aarch64", "armh", "i586", "ppc64le", "x86_64")

        response = self.send_sql_request(
            self.sql.get_subtasks_binaries_with_sources.format(
                task_id=task["task_id"],
                task_try=task["task_try"],
                task_iter=task["task_iter"],
                task_changed=task["task_changed"],
                archs=archs,
            )
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {"Error": f"No data found in database for task '{self.task_id}'"}
            )

        subtasks = [SubtaskWithBinary(*el) for el in response]

        response = self.send_sql_request(
            self.sql.get_task_arepo_packages.format(
                task_id=task["task_id"],
                task_try=task["task_try"],
                task_iter=task["task_iter"],
            )
        )
        if not self.sql_status:
            return self.error
        if response:
            arepo = []
            for subtask in subtasks:
                arepo_base_pkg_name = f"i586-{subtask.binpkg_name}"
                if (
                    subtask.binpkg_arch == "i586"
                    and (arepo_base_pkg_name, subtask.pkg_version, subtask.pkg_release)
                    in response
                ):
                    arepo.append(
                        SubtaskWithBinary(
                            subtask.id,
                            subtask.type,
                            subtask.srpm_name,
                            subtask.srpm_hash,
                            subtask.pkg_version,
                            subtask.pkg_release,
                            arepo_base_pkg_name,
                            "x86_64-i586",
                        )
                    )

            subtasks.extend(arepo)

        _tmp_table = "tmp_pkgs_names"
        response = self.send_sql_request(
            self.sql.get_images_by_binary_pkgs_names.format(
                branch=task["task_repo"], tmp_table=_tmp_table
            ),
            external_tables=[
                {
                    "name": _tmp_table,
                    "structure": [
                        ("pkg_name", "String"),
                    ],
                    "data": [{"pkg_name": s.binpkg_name} for s in subtasks],
                },
            ],
        )
        if not self.sql_status:
            return self.error

        images = [Image(*el) for el in response]

        joined = inner_join(subtasks, images)

        # discard images which binaries are newer and can't be affected by the task
        if task["task_state"] == "DONE":
            # 0 - subtask, 1 - image
            joined = filter(
                lambda entry: entry[1].buildtime <= task["task_changed"], joined
            )

        groupped_by_subtask: dict[Subtask, list[Image]] = defaultdict(list)

        for subtask, image in joined:
            sub = Subtask(*subtask[:6])  # type: ignore
            groupped_by_subtask[sub].append(image)

        task["subtasks"] = sorted(
            [
                {
                    **subtask._asdict(),
                    "images": sorted(
                        [image._asdict() for image in images],
                        key=lambda image: image["filename"],
                    ),
                }
                for subtask, images in groupped_by_subtask.items()
            ],
            key=lambda subtask: subtask["id"],
        )

        return task, 200
