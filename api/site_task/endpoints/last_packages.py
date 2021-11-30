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

from collections import namedtuple

from utils import datetime_to_iso, get_nickname_from_packager

from api.base import APIWorker
from api.misc import lut
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

        if self.args["task_owner"] == "":
            self.validation_results.append(
                f"task owner's nickname should not be empty string"
            )

        if self.args["branch"] == "" or self.args["branch"] not in lut.known_branches:
            self.validation_results.append(
                f"unknown package set name : {self.args['branch']}"
            )
            self.validation_results.append(
                f"allowed package set names are : {lut.known_branches}"
            )

        if self.args["tasks_limit"] and self.args["tasks_limit"] < 1:
            self.validation_results.append(
                f"last tasks limit should be greater or equal to 1"
            )

        if self.validation_results != []:
            return False
        else:
            return True

    def get(self):
        self.branch = self.args["branch"]
        self.tasks_limit = self.args["tasks_limit"]
        self.task_owner = self.args["task_owner"]

        if self.task_owner is not None:
            task_owner_sub = f"AND task_owner = %(task_owner)s"
        else:
            self.task_owner = ""
            task_owner_sub = ""

        self.conn.request_line = (
            self.sql.get_last_subtasks_from_tasks.format(task_owner_sub=task_owner_sub),
            {
                "branch": self.branch,
                "task_owner": self.task_owner,
                "limit": self.tasks_limit,
                "limit2": (self.tasks_limit * 10),
            },
        )
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        if not response:
            self._store_error(
                {
                    "message": f"No data found in database for given parameters",
                    "args": self.args,
                },
                self.ll.INFO,
                404,
            )
            return self.error

        TasksMeta = namedtuple(
            "TasksMeta",
            [
                "task_id",
                "subtask_id",
                "task_owner",
                "task_changed",
                "subtask_userid",
                "subtask_type",
                "subtask_package",
                "subtask_srpm_name",
                "subtask_pkg_from",
                "titer_srcrpm_hash",
                "task_message",
            ],
        )

        tasks = [TasksMeta(*el)._asdict() for el in response]

        src_pkg_hashes = {t["titer_srcrpm_hash"] for t in tasks}

        # create temporary table for source package hashes
        tmp_table = "tmp_srcpkg_hashes"
        self.conn.request_line = self.sql.create_tmp_table.format(
            tmp_table=tmp_table, columns="(pkg_hash UInt64)"
        )
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        # insert package hashes into temporary table
        self.conn.request_line = (
            self.sql.insert_into_tmp_table.format(tmp_table=tmp_table),
            ((x,) for x in src_pkg_hashes),
        )
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        # select packages info by hashes
        self.conn.request_line = self.sql.get_last_pkgs_info.format(tmp_table=tmp_table)
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        if not response:
            self._store_error(
                {
                    "message": f"No data found in database for packages",
                    "args": self.args,
                },
                self.ll.INFO,
                404,
            )
            return self.error

        PkgMeta = namedtuple(
            "PkgMeta",
            [
                "pkg_name",
                "pkg_version",
                "pkg_release",
                "pkg_buildtime",
                "pkg_summary",
                "changelog_name",
                "changelog_date",
                "changelog_text",
            ],
        )

        packages = {el[0]: PkgMeta(*el[1:])._asdict() for el in response}

        retval = {}
        for subtask in tasks:
            task_id = subtask["task_id"]
            if task_id not in retval:
                retval[task_id] = {
                    "task_owner": subtask["task_owner"],
                    "task_changed": datetime_to_iso(subtask["task_changed"]),
                    "task_message": subtask["task_message"],
                    "packages": [],
                }

            pkg_info = {
                "subtask_id": subtask["subtask_id"],
                "subtask_userid": subtask["subtask_userid"],
            }

            if subtask["subtask_type"] in ("gear", "srpm"):
                pkg_info["subtask_type"] = "build"
            elif subtask["subtask_type"] == "rebuild":
                # if task rebuilt from another branch then change type to 'build'
                if subtask["subtask_pkg_from"] != self.branch:
                    pkg_info["subtask_type"] = "build"
                else:
                    pkg_info["subtask_type"] = "rebuild"
            else:
                pkg_info["subtask_type"] = subtask["subtask_type"]

            if subtask["titer_srcrpm_hash"] != 0:
                pkg_info["pkg_hash"] = str(subtask["titer_srcrpm_hash"])
                try:
                    pkg_info.update(
                        {
                            k: v
                            for k, v in packages[subtask["titer_srcrpm_hash"]].items()
                        }
                    )
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
                    if subtask[k] != "":
                        pkg_info["pkg_name"] = subtask[k]
                        break
                # skip tasks with task iterations not inserted from table buffers
                if "pkg_name" not in pkg_info:
                    self.logger.warning(f"No task iteration info. Skip task {task_id}")
                    continue

            retval[task_id]["packages"].append(pkg_info)

        # get last branch task and date
        last_branch_task = 0
        last_branch_date = ""
        if self.branch not in lut.taskless_branches:
            self.conn.request_line = self.sql.get_last_branch_task_and_date.format(
                branch=self.branch
            )
            status, response = self.conn.send_request()
            if not status:
                self._store_sql_error(response, self.ll.ERROR, 500)
                return self.error
            if response:
                last_branch_task = response[0][0]
                last_branch_date = datetime_to_iso(response[0][1])

        retval = [{"task_id": k, **v} for k, v in retval.items()]

        res = {
            "request_args": self.args,
            "length": len(retval),
            "tasks": retval,
            "last_branch_task": last_branch_task,
            "last_branch_date": last_branch_date,
        }
        return res, 200
