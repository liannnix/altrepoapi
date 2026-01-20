# ALTRepo API
# Copyright (C) 2021-2026  BaseALT Ltd

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

from collections import defaultdict, namedtuple

from altrepo_api.utils import (
    join_tuples,
    datetime_to_iso,
    make_tmp_table_name,
    valid_task_id,
)
from altrepo_api.api.base import APIWorker
from altrepo_api.api.task.endpoints.task_repo import TaskRepoState

from ..sql import sql


class TaskDiff(APIWorker):
    """Retrieves task difference from previous repository state."""

    def __init__(self, connection, id, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        self.task_id = id
        super().__init__()

    def check_task_id(self):
        if not valid_task_id(self.task_id):
            return False
        response = self.send_sql_request(self.sql.check_task.format(id=self.task_id))
        if not self.sql_status:
            return False

        return response[0][0] != 0

    def get(self):
        self.tr = TaskRepoState(self.conn, self.task_id)
        self.tr.build_task_repo(keep_artefacts=True)

        if not self.tr.status:
            return self.tr.error

        if not self.tr.have_plan:
            return self.store_error(
                {"Error": f"No package plan for task {self.task_id}"}
            )

        repo_pkgs = self.tr.task_base_repo_pkgs
        task_add_pkgs = self.tr.task_add_pkgs
        task_del_pkgs = self.tr.task_del_pkgs

        tmp_repo_hashes = make_tmp_table_name("repo_hashes")
        _ = self.send_sql_request(
            self.sql.create_tmp_hshs_table.format(table=tmp_repo_hashes)
        )
        if not self.sql_status:
            return self.error

        _ = self.send_sql_request(
            (
                self.sql.insert_into_tmp_hshs_table.format(table=tmp_repo_hashes),
                ({"pkghash": x} for x in repo_pkgs),
            )
        )
        if not self.sql_status:
            return self.error

        result_dict = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))

        # create tmp table with task del packages hashes
        tmp_task_del_hashes = make_tmp_table_name("task_del_hashes")
        _ = self.send_sql_request(
            self.sql.create_tmp_hshs_table.format(table=tmp_task_del_hashes)
        )
        if not self.sql_status:
            return self.error

        if task_del_pkgs:
            _ = self.send_sql_request(
                (
                    self.sql.insert_into_tmp_hshs_table.format(
                        table=tmp_task_del_hashes
                    ),
                    ({"pkghash": x} for x in task_del_pkgs),
                )
            )
            if not self.sql_status:
                return self.error

            response = self.send_sql_request(
                self.sql.diff_packages_by_hshs.format(table=tmp_task_del_hashes)
            )
            if not self.sql_status:
                return self.error

            if response:
                for el in response:
                    p_name, p_arch, p_fname = el  # type: ignore

                    if p_fname.endswith(".src.rpm"):  # type: ignore
                        p_arch = "src"

                    if p_fname not in result_dict[p_arch][p_name]["del"]:
                        result_dict[p_arch][p_name]["del"].append(p_fname)

        # create tmp table with task add packages hashes
        tmp_task_add_hashes = make_tmp_table_name("task_add_hashes")
        _ = self.send_sql_request(
            self.sql.create_tmp_hshs_table.format(table=tmp_task_add_hashes)
        )
        if not self.sql_status:
            return self.error

        if task_add_pkgs:
            _ = self.send_sql_request(
                (
                    self.sql.insert_into_tmp_hshs_table.format(
                        table=tmp_task_add_hashes
                    ),
                    ({"pkghash": x} for x in task_add_pkgs),
                )
            )
            if not self.sql_status:
                return self.error

            response = self.send_sql_request(
                self.sql.diff_packages_by_hshs.format(table=tmp_task_add_hashes)
            )
            if not self.sql_status:
                return self.error

            if response:
                for el in response:
                    p_name, p_arch, p_fname = el  # type: ignore

                    if p_fname.endswith(".src.rpm"):  # type: ignore
                        p_arch = "src"

                    if p_fname not in result_dict[p_arch][p_name]["add"]:
                        result_dict[p_arch][p_name]["add"].append(p_fname)

        DepInfo = namedtuple("DepInfo", ["dp_name", "dp_flag", "dp_version"])
        DepsKey = namedtuple("DepsKey", ["pkg_name", "dp_type", "arch"])

        def build_depends_dict(depends, dp_type_skip=tuple()):
            """Builds depends dictionary with tuple keys."""

            res = {}

            for el in depends:
                key = DepsKey(*el[:3])
                if key.dp_type in dp_type_skip:
                    continue
                if key not in res:
                    res[key] = []
                res[key] += el[3]

            return res

        def decode_dp_flag(dp_flag: int) -> str:
            """Decodes version equality from dp_flag."""

            result = ""

            if dp_flag == 0:
                return result

            if 0x02 & dp_flag:
                result = "<"

            if 0x04 & dp_flag:
                result = ">"

            if 0x08 & dp_flag:
                result += "="

            return result

        def convert_dpinfo_to_string(depinfo: DepInfo) -> str:
            return " ".join(
                (depinfo.dp_name, decode_dp_flag(depinfo.dp_flag), depinfo.dp_version)
            )

        # get package hashes from repo state by names from plan add/delete hashes
        response = self.send_sql_request(
            self.sql.diff_repo_pkgs.format(
                tmp_table1=tmp_repo_hashes,
                tmp_table2=tmp_task_add_hashes,
                tmp_table3=tmp_task_del_hashes,
            )
        )
        if not self.sql_status:
            return self.error

        if task_add_pkgs and task_del_pkgs and not response:
            return self.store_error(
                {
                    "Error": f"Failed to get packages from last_packages for task {self.task_id} diff"
                },
                self.LL.ERROR,
                500,
            )

        repo_pkgs_filtered = join_tuples(response)  # type: ignore

        # get dependencies for packages from current repository state
        _ = self.send_sql_request(
            self.sql.truncate_tmp_table.format(table=tmp_repo_hashes)
        )
        if not self.sql_status:
            return self.error

        _ = self.send_sql_request(
            (
                self.sql.insert_into_tmp_hshs_table.format(table=tmp_repo_hashes),
                ({"pkghash": x} for x in repo_pkgs_filtered),
            )
        )
        if not self.sql_status:
            return self.error

        response = self.send_sql_request(
            self.sql.diff_depends_by_hshs.format(table=tmp_repo_hashes)
        )
        if not self.sql_status:
            return self.error

        repo_deps = build_depends_dict(response)

        # get depends for added packages from task
        response = self.send_sql_request(
            self.sql.diff_depends_by_hshs.format(table=tmp_task_add_hashes)
        )
        if not self.sql_status:
            return self.error

        task_deps_add = build_depends_dict(response)

        # get depends for deleted packages from task
        response = self.send_sql_request(
            self.sql.diff_depends_by_hshs.format(table=tmp_task_del_hashes)
        )
        if not self.sql_status:
            return self.error

        # drop 'require' dependencies for deleted packages
        task_deps_del = build_depends_dict(response, dp_type_skip=("require"))

        for k, v in task_deps_add.items():
            name_, type_, arch_ = k.pkg_name, k.dp_type, k.arch
            task_set = set(v)
            repo_set = set(repo_deps.get(k, []))

            res_list_del = [
                convert_dpinfo_to_string(DepInfo(*dep)) for dep in repo_set - task_set
            ]
            res_list_add = [
                convert_dpinfo_to_string(DepInfo(*dep)) for dep in task_set - repo_set
            ]

            if res_list_del or res_list_add:
                if result_dict[arch_][name_]["deps"] is None:
                    result_dict[arch_][name_]["deps"] = []

                result_dict[arch_][name_]["deps"].append(
                    {
                        "type": type_,
                        "del": res_list_del,
                        "add": res_list_add,
                    }
                )

        for k, v in task_deps_del.items():
            name_, type_, arch_ = k.pkg_name, k.dp_type, k.arch
            task_set = set(v)

            if result_dict[arch_][name_]["deps"] is None:
                result_dict[arch_][name_]["deps"] = []

            result_dict[arch_][name_]["deps"].append(
                {
                    "type": type_,
                    "del": [
                        convert_dpinfo_to_string(DepInfo(*dep)) for dep in task_set
                    ],
                    "add": [],
                }
            )

        result_dict_2 = {"task_id": self.task_id, "task_diff": []}

        for k, v in result_dict.items():
            arch_dict = {"arch": k, "packages": []}

            for pkg, val in v.items():
                arch_dict["packages"].append(
                    {
                        "package": pkg,
                        "del": val["del"],
                        "add": val["add"],
                        "dependencies": val["deps"],
                    }
                )

            result_dict_2["task_diff"].append(arch_dict)

        # set flag if task plan is applied to repository state
        result_dict_2["task_have_plan"] = self.tr.have_plan

        return result_dict_2, 200


class TaskHistory(APIWorker):
    """Retrieves task by given parameters."""

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        self.validation_results = []

        start_task = self.args["start_task"]
        start_date = self.args["start_date"]
        end_task = self.args["end_task"]
        end_date = self.args["end_date"]

        if (start_task == 0 and start_date is None) or (
            start_task != 0 and start_date is not None
        ):
            self.validation_results.append(
                "one and only one start condition argument should be specified"
            )

        if (end_task == 0 and end_date is None) or (
            end_task != 0 and end_date is not None
        ):
            self.validation_results.append(
                "one and only one end condition argument should be specified"
            )

        if start_task and not valid_task_id(start_task):
            self.validation_results.append(f"Invalid 'start_task' value: {start_task}")

        if end_task and not valid_task_id(end_task):
            self.validation_results.append(f"Invalid 'end_task' value: {end_task}")

        if self.validation_results != []:
            return False
        else:
            return True

    def _check_task_id(self, task_id, branch):
        response = self.send_sql_request(
            self.sql.check_task_in_branch.format(id=task_id, branch=branch)
        )
        if not self.sql_status:
            return False

        return response[0][0] != 0

    def _check_branch_has_tasks(self, branch):
        response = self.send_sql_request(
            self.sql.check_branch_has_tasks.format(branch=branch)
        )
        if not self.sql_status:
            return False

        return response[0][0] != 0

    def get(self):
        branch = self.args["branch"]
        start_task = self.args["start_task"]
        end_task = self.args["end_task"]
        start_date = self.args["start_date"]
        end_date = self.args["end_date"]

        if (
            self.args["start_date"] is not None
            and self.args["end_date"] is not None
            and self.args["start_date"] >= self.args["end_date"]
        ):
            return self.store_error(
                {
                    "Error": f"end date ({end_date}) should be greater than start date ({start_date})"
                },
                self.LL.ERROR,
                400,
            )

        # check if branch has tasks
        if not self._check_branch_has_tasks(branch):
            return self.store_error(
                {"Error": f"Branch '{branch}' has no task history"}, self.LL.ERROR, 400
            )

        #  check if start and end tasks is in DB
        for task in (start_task, end_task):
            if task != 0:
                if not self._check_task_id(task, branch):
                    return self.store_error(
                        {
                            "Error": f"Task #{task} not found in DB for branch '{branch}'"
                        },
                        self.LL.ERROR,
                        400,
                    )

        # build task history by given arguments
        # get start date from task
        if start_date is None:
            response = self.send_sql_request(
                self.sql.done_task_last_changed.format(id=start_task)
            )
            if not self.sql_status:
                return self.error
            if not response:
                return self.store_error(
                    {"Error": f"Failed to get data for task {start_task}"},
                    self.LL.ERROR,
                    404,
                )

            start_date = response[0][0]  # type: ignore

        # get end date from task
        if end_date is None:
            response = self.send_sql_request(
                self.sql.done_task_last_changed.format(id=end_task)
            )
            if not self.sql_status:
                return self.error
            if not response:
                return self.store_error(
                    {"Error": f"Failed to get data for task {end_task}"},
                    self.LL.ERROR,
                    404,
                )

            end_date = response[0][0]  # type: ignore
        else:
            end_date = end_date.replace(hour=23, minute=59, second=59)

        if start_date >= end_date:  # type: ignore
            return self.store_error(
                {"Error": "Task history end date should be greater than start date"},
                self.LL.ERROR,
                400,
            )

        # get task history list
        response = self.send_sql_request(
            self.sql.get_task_history.format(
                branch=branch, t1_changed=start_date, t2_changed=end_date
            )
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {"Error": "Failed to get task history"},
                self.LL.ERROR,
                500,
            )

        TaskInfo = namedtuple(
            "TaskInfo", ["task_id", "changed", "pkgset_date", "pkgset_task"]
        )

        task_list = [TaskInfo(*el) for el in response]

        res = {"request_args": self.args, "length": len(task_list), "tasks": []}

        for task in task_list:
            t = {
                "task_id": task.task_id,
                "task_commited": datetime_to_iso(task.changed),
                "branch_commited": "",
            }

            if task.pkgset_task != 0:
                t["branch_commited"] = datetime_to_iso(task.pkgset_date)

            res["tasks"].append(t)

        return res, 200
