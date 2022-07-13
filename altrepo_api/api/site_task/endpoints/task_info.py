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

from collections import namedtuple

from altrepo_api.utils import datetime_to_iso

from altrepo_api.api.base import APIWorker
from altrepo_api.api.misc import lut
from ..sql import sql


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

    @staticmethod
    def _build_gear_link(subtask, git_base_url):
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

        type_ = ""
        link_ = ""
        if subtask["type"] == "copy":
            # 'copy' always has only 'subtask_package'
            type_ = "search"
            link_ = subtask["package"]
            if subtask["pkg_from"] != "":
                link_ += f"&{subtask['pkg_from']}"
        elif subtask["type"] == "delete" and subtask["srpm_name"] != "":
            # FIXME: bug workaround for girar changes @ e74d8067009d
            type_ = "srpm"
            link_ = f"{git_base_url}/srpms/{subtask['srpm_name'][0]}/{subtask['srpm_name']}.git"
            if subtask["srpm_evr"] != "":
                link_ += f"?a=tree;hb={delete_epoch(subtask['srpm_evr'])}"
        elif subtask["type"] == "delete":
            # 'delete' return only package name
            type_ = "delete"
            link_ = subtask["package"]
        elif subtask["dir"] != "" or subtask["type"] == "gear":
            # 'gear' and 'rebuild' + 'unknown' with gears
            type_ = "gear"
            link_ = git_base_url + subtask["dir"]
            if subtask["tag_id"] != "":
                link_ += f"?a=tree;hb={subtask['tag_id']}"
        elif subtask["srpm_name"] != "" or subtask["type"] == "srpm":
            # 'srpm' and 'rebuild' + 'unknown' with srpm
            type_ = "srpm"
            link_ = f"{git_base_url}/srpms/{subtask['srpm_name'][0]}/{subtask['srpm_name']}.git"
            if subtask["srpm_evr"] != "":
                link_ += f"?a=tree;hb={delete_epoch(subtask['srpm_evr'])}"

        return type_, link_

    def get(self):
        self.name = self.args["name"]

        self.conn.request_line = self.sql.get_tasks_by_pkg_name.format(name=self.name)
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error

        if not response:
            self._store_error(
                {"message": f"No data found in database for package '{self.name}'"},
                self.ll.INFO,
                404,
            )
            return self.error

        TaskMeta = namedtuple("TaskMeta", ["id", "state", "changed", "packages"])
        retval = [TaskMeta(*el)._asdict() for el in response]

        tasks_for_pkg_names_search = []
        pkg_names = {}

        for task in retval:
            for s in task["packages"]:
                tasks_for_pkg_names_search.append((s[0], s[1]))

        if len(tasks_for_pkg_names_search) != 0:
            # create temporary table with task_id, subtask_id
            tmp_table = "tmp_task_ids"
            self.conn.request_line = self.sql.create_tmp_table.format(
                tmp_table=tmp_table, columns="(task_id UInt32, subtask_id UInt32)"
            )
            status, response = self.conn.send_request()
            if not status:
                self._store_sql_error(response, self.ll.ERROR, 500)
                return self.error
            # insert task_id, subtask_id into temporary table
            self.conn.request_line = (
                self.sql.insert_into_tmp_table.format(tmp_table=tmp_table),
                (
                    {"task_id": int(el[0]), "subtask_id": int(el[1])}
                    for el in tasks_for_pkg_names_search
                ),
            )
            status, response = self.conn.send_request()
            if not status:
                self._store_sql_error(response, self.ll.ERROR, 500)
                return self.error
            # select package names by (task_id, subtask_id)
            self.conn.request_line = self.sql.get_pkg_names_by_task_ids.format(
                tmp_table=tmp_table
            )
            status, response = self.conn.send_request()
            if not status:
                self._store_sql_error(response, self.ll.ERROR, 500)
                return self.error
            if response:
                pkg_names = {(el[0], el[1]): el[2:] for el in response if el[2] != ""}  # type: ignore

        res = []
        SubtaskMeta = namedtuple(
            "SubtaskMeta",
            [
                "id",
                "sub_id",
                "repo",
                "owner",
                "type",
                "dir",
                "tag_id",
                "srpm_name",
                "srpm_evr",
                "package",
                "pkg_from",
                "changed",
            ],
        )
        for task in retval:
            pkg_ls = []
            pkg_type = ""
            pkg_link = ""
            pkg_name = ""
            pkg_version = ""
            pkg_release = ""
            for s in task["packages"]:
                subtask = SubtaskMeta(*s)._asdict()
                pkg_name, pkg_version, pkg_release = pkg_names.get(  # type: ignore
                    (int(subtask["id"]), int(subtask["sub_id"])), ("", "", "")
                )
                if subtask["package"] != "":
                    pkg_name = subtask["package"]
                elif subtask["srpm_name"] != "":
                    pkg_name = subtask["srpm_name"]
                if subtask["dir"] != "" and not subtask["dir"].startswith("/gears/"):
                    if pkg_name:
                        subtask["dir"] = f"/gears/{pkg_name[0]}/{pkg_name}.git"
                    else:
                        pkg_name = subtask["dir"].split("/")[-1][:-4]
                elif subtask["dir"].startswith("/gears/"):
                    pkg_name = subtask["dir"].split("/")[-1][:-4]
                pkg_type, pkg_link = self._build_gear_link(subtask, lut.gitalt_base)
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
                    "id": task["id"],
                    "state": task["state"],
                    "changed": datetime_to_iso(task["changed"]),
                    "branch": task["packages"][0][2],
                    "owner": task["packages"][0][3],
                    "packages": pkg_ls,
                }
            )

        res = {"request_args": self.args, "length": len(res), "tasks": res}
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

        self.conn.request_line = self.sql.get_tasks_by_maintainer.format(
            maintainer_nickname=maintainer_nickname, branch=branch
        )
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error

        if not response:
            self._store_error(
                {"message": "No data not found in database", "args": self.args},
                self.ll.INFO,
                404,
            )
            return self.error

        TaskMeta = namedtuple("TaskMeta", ["id", "state", "changed", "packages"])
        retval = [TaskMeta(*el)._asdict() for el in response]

        tasks_for_pkg_names_search = []
        pkg_names = {}

        for task in retval:
            for s in task["packages"]:
                tasks_for_pkg_names_search.append((s[0], s[1]))

        if len(tasks_for_pkg_names_search) != 0:
            # create temporary table with task_id, subtask_id
            tmp_table = "tmp_task_ids"
            self.conn.request_line = self.sql.create_tmp_table.format(
                tmp_table=tmp_table, columns="(task_id UInt32, subtask_id UInt32)"
            )
            status, response = self.conn.send_request()
            if not status:
                self._store_sql_error(response, self.ll.ERROR, 500)
                return self.error
            # insert task_id, subtask_id into temporary table
            self.conn.request_line = (
                self.sql.insert_into_tmp_table.format(tmp_table=tmp_table),
                (
                    {"task_id": int(el[0]), "subtask_id": int(el[1])}
                    for el in tasks_for_pkg_names_search
                ),
            )
            status, response = self.conn.send_request()
            if not status:
                self._store_sql_error(response, self.ll.ERROR, 500)
                return self.error
            # select package names by (task_id, subtask_id)
            self.conn.request_line = self.sql.get_pkg_names_by_task_ids.format(
                tmp_table=tmp_table
            )
            status, response = self.conn.send_request()
            if not status:
                self._store_sql_error(response, self.ll.ERROR, 500)
                return self.error
            if response:
                pkg_names = {(el[0], el[1]): el[2:] for el in response if el[2] != ""}  # type: ignore

        res = []
        SubtaskMeta = namedtuple(
            "SubtaskMeta",
            [
                "id",
                "sub_id",
                "repo",
                "owner",
                "type",
                "dir",
                "tag_id",
                "srpm_name",
                "srpm_evr",
                "package",
                "pkg_from",
                "changed",
            ],
        )
        for task in retval:
            pkg_ls = []
            pkg_type = ""
            pkg_link = ""
            pkg_name = ""
            pkg_version = ""
            pkg_release = ""
            for s in task["packages"]:
                subtask = SubtaskMeta(*s)._asdict()
                pkg_name, pkg_version, pkg_release = pkg_names.get(  # type: ignore
                    (int(subtask["id"]), int(subtask["sub_id"])), ("", "", "")
                )
                if subtask["package"] != "":
                    pkg_name = subtask["package"]
                elif subtask["srpm_name"] != "":
                    pkg_name = subtask["srpm_name"]
                if subtask["dir"] != "" and not subtask["dir"].startswith("/gears/"):
                    if pkg_name:
                        subtask["dir"] = f"/gears/{pkg_name[0]}/{pkg_name}.git"
                    else:
                        pkg_name = subtask["dir"].split("/")[-1][:-4]
                elif subtask["dir"].startswith("/gears/"):
                    pkg_name = subtask["dir"].split("/")[-1][:-4]
                pkg_type, pkg_link = TasksByPackage._build_gear_link(
                    subtask, lut.gitalt_base
                )
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
                    "id": task["id"],
                    "state": task["state"],
                    "changed": datetime_to_iso(task["changed"]),
                    "branch": task["packages"][0][2],
                    "owner": task["packages"][0][3],
                    "packages": pkg_ls,
                }
            )

        res = {"request_args": self.args, "length": len(res), "tasks": res}
        return res, 200
