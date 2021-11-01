from copy import deepcopy
from collections import defaultdict, namedtuple

from utils import join_tuples, remove_duplicate

from api.base import APIWorker
from api.misc import lut
from ..sql import sql
from api.task.endpoints.task_repo import TaskRepoState


class TaskDiff(APIWorker):
    """Retrieves task difference from previous repository state."""

    def __init__(self, connection, id, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        self.task_id = id
        super().__init__()

    def check_task_id(self):
        self.conn.request_line = self.sql.check_task.format(id=self.task_id)
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.INFO, 500)
            return False

        if response[0][0] == 0:
            return False
        return True

    def get(self):
        self.tr = TaskRepoState(self.conn, self.task_id)
        self.tr.build_task_repo(keep_artefacts=True)
        if not self.tr.status:
            return self.tr.error

        if not self.tr.have_plan:
            self._store_sql_error(
                {"Error": f"No package plan for task {self.task_id}"},
                self.ll.ERROR,
                404,
            )
            return self.error

        repo_pkgs = self.tr.task_base_repo_pkgs
        task_add_pkgs = self.tr.task_add_pkgs
        task_del_pkgs = self.tr.task_del_pkgs

        self.conn.request_line = self.sql.create_tmp_hshs_table.format(
            table="tmpRepoHshs"
        )
        status, response = self.conn.send_request()
        if status is False:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error

        self.conn.request_line = (
            self.sql.insert_into_tmp_hshs_table.format(table="tmpRepoHshs"),
            ({"pkghash": x} for x in repo_pkgs),
        )
        status, response = self.conn.send_request()
        if status is False:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error

        result_dict = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))

        # create tmp table with task del packages hashes
        self.conn.request_line = self.sql.create_tmp_hshs_table.format(
            table="tmpTaskDelHshs"
        )
        status, response = self.conn.send_request()
        if status is False:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error

        if task_del_pkgs:
            self.conn.request_line = (
                self.sql.insert_into_tmp_hshs_table.format(table="tmpTaskDelHshs"),
                ({"pkghash": x} for x in task_del_pkgs),
            )
            status, response = self.conn.send_request()
            if status is False:
                self._store_sql_error(response, self.ll.ERROR, 500)
                return self.error

            self.conn.request_line = self.sql.diff_packages_by_hshs.format(
                table="tmpTaskDelHshs"
            )
            status, response = self.conn.send_request()
            if status is False:
                self._store_sql_error(response, self.ll.ERROR, 500)
                return self.error

            if response:
                for el in response:
                    p_name, p_arch, p_fname = el
                    if p_fname.endswith(".src.rpm"):
                        p_arch = "src"
                    if p_fname not in result_dict[p_arch][p_name]["del"]:
                        result_dict[p_arch][p_name]["del"].append(p_fname)

        # create tmp table with task add packages hashes
        self.conn.request_line = self.sql.create_tmp_hshs_table.format(
            table="tmpTaskAddHshs"
        )
        status, response = self.conn.send_request()
        if status is False:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error

        if task_add_pkgs:
            self.conn.request_line = (
                self.sql.insert_into_tmp_hshs_table.format(table="tmpTaskAddHshs"),
                ({"pkghash": x} for x in task_add_pkgs),
            )
            status, response = self.conn.send_request()
            if status is False:
                self._store_sql_error(response, self.ll.ERROR, 500)
                return self.error

            self.conn.request_line = self.sql.diff_packages_by_hshs.format(
                table="tmpTaskAddHshs"
            )
            status, response = self.conn.send_request()
            if status is False:
                self._store_sql_error(response, self.ll.ERROR, 500)
                return self.error

            if response:
                for el in response:
                    p_name, p_arch, p_fname = el
                    if p_fname.endswith(".src.rpm"):
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
            result = " ".join(
                (depinfo.dp_name, decode_dp_flag(depinfo.dp_flag), depinfo.dp_version)
            )
            return result

        # get package hashes from repo state by names from plan add/delete hashes
        self.conn.request_line = self.sql.diff_repo_pkgs.format(
            tmp_table1="tmpRepoHshs",
            tmp_table2="tmpTaskAddHshs",
        )
        status, response = self.conn.send_request()
        if status is False:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error

        if task_add_pkgs and task_del_pkgs and not response:
            self._store_sql_error(
                {
                    "Error": f"Failed to get packages from last_packages for task {self.task_id} diff"
                },
                self.ll.ERROR,
                500,
            )
            return self.error

        repo_pkgs_filtered = join_tuples(response)

        # get dependencies for packages from current repository state
        self.conn.request_line = self.sql.truncate_tmp_table.format(table="tmpRepoHshs")
        status, response = self.conn.send_request()
        if status is False:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error

        self.conn.request_line = (
            self.sql.insert_into_tmp_hshs_table.format(table="tmpRepoHshs"),
            ({"pkghash": x} for x in repo_pkgs_filtered),
        )
        status, response = self.conn.send_request()
        if status is False:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error

        self.conn.request_line = self.sql.diff_depends_by_hshs.format(
            table="tmpRepoHshs"
        )
        status, response = self.conn.send_request()
        if status is False:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error

        repo_deps = build_depends_dict(response)

        # get depends for added packages from task
        self.conn.request_line = self.sql.diff_depends_by_hshs.format(
            table="tmpTaskAddHshs"
        )
        status, response = self.conn.send_request()
        if status is False:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error

        task_deps_add = build_depends_dict(response)

        # get depends for added packages from task
        self.conn.request_line = self.sql.diff_depends_by_hshs.format(
            table="tmpTaskDelHshs"
        )
        status, response = self.conn.send_request()
        if status is False:
            self._store_sql_error(response, self.ll.ERROR, 500)
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
