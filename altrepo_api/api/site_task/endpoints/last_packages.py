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

from datetime import datetime
from typing import NamedTuple

from altrepo_api.utils import (
    datetime_to_iso,
    get_nickname_from_packager,
    make_tmp_table_name,
)

from altrepo_api.api.base import APIWorker
from altrepo_api.api.misc import lut
from ..sql import sql


class LastTaskPackages(APIWorker):
    """Retrieves packages information from last tasks."""

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        self.validation_results = []

        if self.args["tasks_limit"] < 1:
            self.validation_results.append(
                "last tasks limit should be greater or equal to 1"
            )

        if self.validation_results != []:
            return False
        else:
            return True

    def get(self):
        branch = self.args["branch"]
        task_owner = self.args["task_owner"]
        tasks_limit = self.args["tasks_limit"]

        if task_owner is not None:
            last_tasks_preselect = (
                self.sql.get_last_subtasks_maintainer_preselect.format(
                    branch=branch, task_owner=task_owner, limit=tasks_limit
                )
            )
        else:
            last_tasks_preselect = self.sql.get_last_subtasks_branch_preselect.format(
                branch=branch, limit=tasks_limit
            )

        response = self.send_sql_request(
            (
                self.sql.get_last_subtasks_from_tasks.format(
                    last_tasks_preselect=last_tasks_preselect
                )
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

        class Subtask(NamedTuple):
            task_id: int
            subtask_id: int
            task_owner: str
            task_changed: datetime
            subtask_userid: str
            subtask_type: str
            subtask_package: str
            subtask_srpm_name: str
            subtask_pkg_from: str
            titer_srcrpm_hash: int
            task_message: str

        subtasks = [Subtask(*el) for el in response]

        src_pkg_hashes = {t.titer_srcrpm_hash for t in subtasks}

        # create temporary table for source package hashes
        tmp_table = make_tmp_table_name("srcpkg_hashes")

        _ = self.send_sql_request(
            self.sql.create_tmp_table.format(
                tmp_table=tmp_table, columns="(pkg_hash UInt64)"
            )
        )
        if not self.sql_status:
            return self.error

        # insert package hashes into temporary table
        _ = self.send_sql_request(
            (
                self.sql.insert_into_tmp_table.format(tmp_table=tmp_table),
                ((x,) for x in src_pkg_hashes),
            )
        )
        if not self.sql_status:
            return self.error

        # select packages info by hashes
        response = self.send_sql_request(
            self.sql.get_last_pkgs_info.format(tmp_table=tmp_table)
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

        class Package(NamedTuple):
            pkg_name: str
            pkg_version: str
            pkg_release: str
            pkg_buildtime: int
            pkg_summary: str
            changelog_name: str
            changelog_date: str
            changelog_text: str

        packages: dict[int, Package] = {el[0]: Package(*el[1:]) for el in response}

        retval = {}

        for subtask in subtasks:
            task_id = subtask.task_id
            if task_id not in retval:
                retval[task_id] = {
                    "task_owner": subtask.task_owner,
                    "task_changed": datetime_to_iso(subtask.task_changed),
                    "task_message": subtask.task_message,
                    "packages": [],
                }

            pkg_info = {
                "subtask_id": subtask.subtask_id,
                "subtask_userid": subtask.subtask_userid,
            }

            if subtask.subtask_type in ("gear", "srpm"):
                pkg_info["subtask_type"] = "build"
            elif subtask.subtask_type == "rebuild":
                # if task rebuilt from another branch then change type to 'build'
                if subtask.subtask_pkg_from != branch:
                    pkg_info["subtask_type"] = "build"
                else:
                    pkg_info["subtask_type"] = "rebuild"
            else:
                pkg_info["subtask_type"] = subtask.subtask_type

            if subtask.titer_srcrpm_hash != 0:
                pkg_info["pkg_hash"] = str(subtask.titer_srcrpm_hash)
                try:
                    pkg_info.update(packages[subtask.titer_srcrpm_hash]._asdict())
                except KeyError:
                    # skip task with packages not inserted from table buffers
                    self.logger.warning(f"No package info. Skip task {task_id}")
                    continue
                pkg_info["changelog_date"] = datetime_to_iso(pkg_info["changelog_date"])
                pkg_info["changelog_nickname"] = get_nickname_from_packager(
                    pkg_info["changelog_name"]
                )
            else:
                pkg_info["pkg_hash"] = ""
                for k in ("subtask_package", "subtask_srpm_name"):
                    value = getattr(subtask, k, None)
                    if value != "":
                        pkg_info["pkg_name"] = value
                        break
                # skip tasks with task iterations not inserted from table buffers
                if "pkg_name" not in pkg_info:
                    self.logger.warning(f"No task iteration info. Skip task {task_id}")
                    continue

            retval[task_id]["packages"].append(pkg_info)

        # get last branch task and date
        last_branch_task = 0
        last_branch_date = ""

        if branch not in lut.taskless_branches:
            response = self.send_sql_request(
                self.sql.get_last_branch_task_and_date.format(branch=branch)
            )
            if not self.sql_status:
                return self.error

            if response:
                last_branch_task = response[0][0]  # type: ignore
                last_branch_date = datetime_to_iso(response[0][1])  # type: ignore

        retval = [{"task_id": k, **v} for k, v in retval.items()]

        res = {
            "request_args": self.args,
            "length": len(retval),
            "tasks": retval,
            "last_branch_task": last_branch_task,
            "last_branch_date": last_branch_date,
        }

        return res, 200
