from collections import namedtuple

from utils import datetime_to_iso

from api.base import APIWorker
from api.misc import lut
from database.site_sql import sitesql


class TasksByPackage(APIWorker):
    """Retrieves tasks information by package name."""

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sitesql
        super().__init__()

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        self.validation_results = []

        if self.args["name"] == "":
            self.validation_results.append(f"package name should not be empty string")

        if self.validation_results != []:
            return False
        else:
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
                link_ += f"?a=commit;hb={subtask['srpm_evr']}"
        elif subtask["type"] == "delete":
            # 'delete' return only package name
            type_ = "delete"
            link_ = subtask["package"]
        elif subtask["dir"] != "" or subtask["type"] == "gear":
            # 'gear' and 'rebuild' + 'unknown' with gears
            type_ = "gear"
            link_ = git_base_url + subtask["dir"]
            if subtask["tag_id"] != "":
                link_ += f"?a=commit;hb={subtask['tag_id']}"
        elif subtask["srpm_name"] != "" or subtask["type"] == "srpm":
            # 'srpm' and 'rebuild' + 'unknown' with srpm
            type_ = "srpm"
            link_ = f"{git_base_url}/srpms/{subtask['srpm_name'][0]}/{subtask['srpm_name']}.git"
            if subtask["srpm_evr"] != "":
                link_ += f"?a=commit;hb={subtask['srpm_evr']}"

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
                if s[5] != "" and not s[5].startswith("/gears/"):
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
                pkg_names = {(el[0], el[1]): el[2] for el in response if el[2] != ""}

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
            for s in task["packages"]:
                subtask = SubtaskMeta(*s)._asdict()
                if subtask["package"] != "":
                    pkg_name = subtask["package"]
                elif subtask["srpm_name"] != "":
                    pkg_name = subtask["srpm_name"]
                if subtask["dir"] != "" and not subtask["dir"].startswith("/gears/"):
                    try:
                        pkg_name = pkg_names[
                            (int(subtask["id"]), int(subtask["sub_id"]))
                        ]
                        subtask["dir"] = f"/gears/{pkg_name[0]}/{pkg_name}.git"
                    except KeyError:
                        pkg_name = subtask["dir"].split("/")[-1][:-4]
                elif subtask["dir"].startswith("/gears/"):
                    pkg_name = subtask["dir"].split("/")[-1][:-4]
                pkg_type, pkg_link = self._build_gear_link(subtask, lut.gitalt_base)
                pkg_ls.append({"type": pkg_type, "link": pkg_link, "name": pkg_name})

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


class LastTaskPackages(APIWorker):
    """Retrieves packages information from last tasks."""

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sitesql
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

        retval = [{"task_id": k, **v} for k, v in retval.items()]

        res = {"request_args": self.args, "length": len(retval), "tasks": retval}
        return res, 200


class TasksByMaintainer(APIWorker):
    """Retrieves tasks information by maintainer."""

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sitesql
        super().__init__()

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        self.validation_results = []

        if self.args["branch"] == "" or self.args["branch"] not in lut.known_branches:
            self.validation_results.append(
                f"unknown package set name : {self.args['branch']}"
            )
            self.validation_results.append(
                f"allowed package set names are : {lut.known_branches}"
            )

        if self.args["maintainer_nickname"] == "":
            self.validation_results.append(
                f"maintainer nickname should not be empty string"
            )

        if self.validation_results != []:
            return False
        else:
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
                {"message": f"No data not found in database", "args": self.args},
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
                if s[5] != "" and not s[5].startswith("/gears/"):
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
                pkg_names = {(el[0], el[1]): el[2] for el in response if el[2] != ""}

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
            pkg_name = ""
            for s in task["packages"]:
                subtask = SubtaskMeta(*s)._asdict()
                if subtask["package"] != "":
                    pkg_name = subtask["package"]
                elif subtask["srpm_name"] != "":
                    pkg_name = subtask["srpm_name"]
                if subtask["dir"] != "" and not subtask["dir"].startswith("/gears/"):
                    try:
                        pkg_name = pkg_names[
                            (int(subtask["id"]), int(subtask["sub_id"]))
                        ]
                        subtask["dir"] = f"/gears/{pkg_name[0]}/{pkg_name}.git"
                    except Exception as e:
                        pkg_name = subtask["dir"].split("/")[-1][:-4]
                elif subtask["dir"].startswith("/gears/"):
                    pkg_name = subtask["dir"].split("/")[-1][:-4]
                pkg_type, pkg_link = TasksByPackage._build_gear_link(
                    subtask, lut.gitalt_base
                )
                pkg_ls.append({"type": pkg_type, "link": pkg_link, "name": pkg_name})

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
