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
from typing import Any, Iterable, NamedTuple

from altrepo_api.utils import datetime_to_iso, make_tmp_table_name
from altrepo_api.api.base import APIWorker
from altrepo_api.api.misc import lut

from ..sql import sql


class SubtaskMeta(NamedTuple):
    id: int
    sub_id: int
    repo: str
    owner: str
    type: str
    dir: str
    tag_id: str
    srpm_name: str
    srpm_evr: str
    package: str
    pkg_from: str
    changed: datetime
    srpm: str = ""


class TaskMeta(NamedTuple):
    id: int
    state: str
    changed: datetime
    packages: list[SubtaskMeta]


def _build_gear_link(
    subtask: SubtaskMeta, git_base_url: str = lut.gitalt_base
) -> tuple[str, str]:
    """Parse task gears

    Args:
        pkg (dict): subtask info with keys:
            ['type', 'dir', 'tag_id', 'srpm_name', 'srpm_evr', 'package', 'pkg_from']

        git_base_url (str): base git url for links ('http://git.altlinux.org')

    Returns:
        tuple: return package type [gear|srpm|copy|delete] and link (git)
    """

    def delete_epoch(evr):
        #  delete epoch from evr
        if ":" in evr:
            return evr.split(":")[-1]
        return evr

    def fix_srpm_name_evr():
        if subtask.srpm.endswith(".src.rpm"):
            pkg_name = subtask.srpm.replace(".src.rpm", "")
        else:
            return subtask

        evr = pkg_name.split("-")[-2:]
        if len(evr) == 2 and evr[1].startswith("alt"):
            version, release = evr
        else:
            return subtask

        return subtask._replace(
            srpm_name=pkg_name.replace(f"-{version}-{release}", ""),
            srpm_evr=f"{delete_epoch(version)}-{release}"
        )

    type_ = ""
    link_ = ""
    if subtask.type == "copy":
        # 'copy' always has only 'subtask_package'
        type_ = "search"
        link_ = subtask.package
        if subtask.pkg_from != "":
            link_ += f"&{subtask.pkg_from}"
    elif subtask.type == "delete" and subtask.srpm_name != "":
        # FIXME: bug workaround for girar changes @ e74d8067009d
        type_ = "srpm"
        link_ = f"{git_base_url}/srpms/{subtask.srpm_name[0]}/{subtask.srpm_name}.git"
        if subtask.srpm_evr != "":
            link_ += f"?a=tree;hb={delete_epoch(subtask.srpm_evr)}"
    elif subtask.type == "delete":
        # 'delete' return only package name
        type_ = "delete"
        link_ = subtask.package
    elif subtask.dir != "" or subtask.type == "gear":
        # 'gear' and 'rebuild' + 'unknown' with gears
        type_ = "gear"
        link_ = git_base_url + subtask.dir
        if subtask.tag_id != "":
            link_ += f"?a=tree;hb={subtask.tag_id}"
    elif subtask.srpm_name != "" or subtask.type == "srpm" or subtask.srpm != "":
        # 'srpm' and 'rebuild' + 'unknown' with srpm
        if subtask.srpm_name == "":
            # handle data from TaskSubtaskProgress with empty `srpm_name` and `srpm_evr`
            subtask = fix_srpm_name_evr()

        type_ = "srpm"
        link_ = f"{git_base_url}/srpms/{subtask.srpm_name[0]}/{subtask.srpm_name}.git"
        if subtask.srpm_evr != "":
            link_ += f"?a=tree;hb={delete_epoch(subtask.srpm_evr)}"

    return type_, link_


def _process_tasks(
    tasks: Iterable[TaskMeta], pkg_names: dict[tuple[int, int], tuple[str, ...]]
) -> list[dict[str, Any]]:
    res = []

    for task in tasks:
        pkg_ls = []
        pkg_type = ""
        pkg_link = ""
        pkg_name = ""
        pkg_version = ""
        pkg_release = ""

        for subtask in task.packages:
            pkg_name, pkg_version, pkg_release = pkg_names.get(
                (subtask.id, subtask.sub_id), ("", "", "")
            )

            if subtask.package != "":
                pkg_name = subtask.package
            elif subtask.srpm_name != "":
                pkg_name = subtask.srpm_name

            if subtask.dir != "" and not subtask.dir.startswith("/gears/"):
                if pkg_name:
                    # XXX: replace `/people/%maintainer%/packages/*` like links with git one
                    subtask = subtask._replace(
                        dir=f"/gears/{pkg_name[0]}/{pkg_name}.git"
                    )
                else:
                    pkg_name = subtask.dir.split("/")[-1][:-4]
            elif subtask.dir.startswith("/gears/"):
                pkg_name = subtask.dir.split("/")[-1][:-4]

            pkg_type, pkg_link = _build_gear_link(subtask)

            pkg_ls.append(
                {
                    "type": pkg_type,
                    "link": pkg_link,
                    "name": pkg_name,
                    "version": pkg_version,
                    "release": pkg_release,
                }
            )

        res.append(
            {
                "id": task.id,
                "state": task.state,
                "changed": datetime_to_iso(task.changed),
                "branch": task.packages[0].repo,
                "owner": task.packages[0].owner,
                "packages": pkg_ls,
            }
        )

    return res


class TasksByPackage(APIWorker):
    """Retrieves tasks information by package name."""

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        return True

    def get(self):
        self.name = self.args["name"]

        response = self.send_sql_request(
            self.sql.get_tasks_by_pkg_name.format(name=self.name)
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {"message": f"No data found in database for package '{self.name}'"}
            )

        tasks = [
            TaskMeta(*el[0:3], packages=[SubtaskMeta(*s) for s in el[3]])
            for el in response
        ]

        pkg_names = {}

        tasks_for_pkg_names_search = [
            (s.id, s.sub_id) for t in tasks for s in t.packages
        ]

        if len(tasks_for_pkg_names_search) != 0:
            # create temporary table with task_id, subtask_id
            tmp_table = make_tmp_table_name("task_ids")

            _ = self.send_sql_request(
                self.sql.create_tmp_table.format(
                    tmp_table=tmp_table, columns="(task_id UInt32, subtask_id UInt32)"
                )
            )
            if not self.sql_status:
                return self.error

            # insert task_id, subtask_id into temporary table
            _ = self.send_sql_request(
                (
                    self.sql.insert_into_tmp_table.format(tmp_table=tmp_table),
                    (
                        {"task_id": el[0], "subtask_id": el[1]}
                        for el in tasks_for_pkg_names_search
                    ),
                )
            )
            if not self.sql_status:
                return self.error

            # select package names by (task_id, subtask_id)
            response = self.send_sql_request(
                self.sql.get_pkg_names_by_task_ids.format(tmp_table=tmp_table)
            )
            if not self.sql_status:
                return self.error

            if response:
                pkg_names = {(el[0], el[1]): el[2:] for el in response if el[2] != ""}

        res_ = _process_tasks(tasks, pkg_names)
        res = {"request_args": self.args, "length": len(res_), "tasks": res_}

        return res, 200


class TasksByMaintainer(APIWorker):
    """Retrieves tasks information by maintainer."""

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        return True

    def get(self):
        maintainer_nickname = self.args["maintainer_nickname"]
        branch = self.args["branch"]

        response = self.send_sql_request(
            self.sql.get_tasks_by_maintainer.format(
                maintainer_nickname=maintainer_nickname, branch=branch
            )
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {"message": "No data not found in database", "args": self.args}
            )

        tasks = [
            TaskMeta(*el[0:3], packages=[SubtaskMeta(*s) for s in el[3]])
            for el in response
        ]

        pkg_names = {}

        tasks_for_pkg_names_search = [
            (s.id, s.sub_id) for t in tasks for s in t.packages
        ]

        if len(tasks_for_pkg_names_search) != 0:
            # create temporary table with task_id, subtask_id
            tmp_table = make_tmp_table_name("task_ids")

            _ = self.send_sql_request(
                self.sql.create_tmp_table.format(
                    tmp_table=tmp_table, columns="(task_id UInt32, subtask_id UInt32)"
                )
            )
            if not self.sql_status:
                return self.error

            # insert task_id, subtask_id into temporary table
            _ = self.send_sql_request(
                (
                    self.sql.insert_into_tmp_table.format(tmp_table=tmp_table),
                    (
                        {"task_id": el[0], "subtask_id": el[1]}
                        for el in tasks_for_pkg_names_search
                    ),
                )
            )
            if not self.sql_status:
                return self.error

            # select package names by (task_id, subtask_id)
            response = self.send_sql_request(
                self.sql.get_pkg_names_by_task_ids.format(tmp_table=tmp_table)
            )
            if not self.sql_status:
                return self.error

            if response:
                pkg_names = {(el[0], el[1]): el[2:] for el in response if el[2] != ""}

        # exclude `DELETED` tasks from result
        res_ = _process_tasks((t for t in tasks if t.state != "DELETED"), pkg_names)
        res = {"request_args": self.args, "length": len(res_), "tasks": res_}

        return res, 200
