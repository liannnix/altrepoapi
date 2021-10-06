from collections import defaultdict

from utils import join_tuples, mmhash

from api.base import APIWorker
from database.task_sql import tasksql


class TaskRepo(APIWorker):
    """Builds package set state from task."""

    def __init__(self, connection, id, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = tasksql
        self.task_id = id
        self.repo = {}
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

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        self.validation_results = []

        if self.args["include_task_packages"] is not None and self.args[
            "include_task_packages"
        ] not in (True, False):
            self.validation_results.append(
                f"'include_task_packages' argument should be one of [0|1|true|false]"
            )

        if self.validation_results != []:
            return False
        else:
            return True

    def build_task_repo(self):
        if not self.check_task_id():
            self._store_sql_error(
                {"Error": f"Non-existent task {self.task_id}"}, self.ll.ERROR, 404
            )
            return None

        self.conn.request_line = self.sql.task_repo.format(id=self.task_id)
        status, response = self.conn.send_request()
        if status is False:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.repo
        if not response:
            self._store_sql_error(
                {"Error": f"Non-existent data for task {self.task_id}"},
                self.ll.ERROR,
                500,
            )
            return None

        task_repo = response[0][0]

        self.conn.request_line = self.sql.repo_task_content.format(id=self.task_id)
        status, response = self.conn.send_request()
        if status is False:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return None
        if not response:
            self._store_sql_error(
                {"Error": f"Non-existent data for task {self.task_id}"},
                self.ll.ERROR,
                500,
            )
            return None

        task_archs = set(("src", "noarch", "x86_64-i586"))
        task_try = 0
        task_iter = 0
        for el in response:
            task_archs.add(el[0])
            task_try = el[1]
            task_iter = el[2]

        task_tplan_hashes = set()
        for arch in task_archs:
            t = str(self.task_id) + str(task_try) + str(task_iter) + arch
            task_tplan_hashes.add(mmhash(t))

        self.conn.request_line = (
            self.sql.repo_single_task_plan_hshs,
            {"hshs": tuple(task_tplan_hashes), "act": "add"},
        )
        status, response = self.conn.send_request()
        if status is False:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return None
        if response:
            task_add_pkgs = set(join_tuples(response))
        else:
            task_add_pkgs = set()

        self.conn.request_line = (
            self.sql.repo_single_task_plan_hshs,
            {"hshs": tuple(task_tplan_hashes), "act": "delete"},
        )
        status, response = self.conn.send_request()
        if status is False:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return None
        if response:
            task_del_pkgs = set(join_tuples(response))
        else:
            task_del_pkgs = set()

        self.conn.request_line = self.sql.repo_tasks_diff_list_before_task.format(
            id=self.task_id, repo=task_repo
        )
        status, response = self.conn.send_request()
        if status is False:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return None

        tasks_diff_list = []
        if response:
            tasks_diff_list += {el[0] for el in response}

        self.conn.request_line = self.sql.repo_last_repo_hashes_before_task.format(
            id=self.task_id, repo=task_repo
        )
        status, response = self.conn.send_request()
        if status is False:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return None
        if not response:
            self._store_sql_error(
                {"Error": f"Failed to get last repo packages for task {self.task_id}"},
                self.ll.ERROR,
                500,
            )
            return None

        last_repo_pkgs = set(join_tuples(response))

        self.conn.request_line = self.sql.repo_last_repo_content.format(
            id=self.task_id, repo=task_repo
        )
        status, response = self.conn.send_request()
        if status is False:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return None
        if not response:
            self._store_sql_error(
                {"Error": f"Failed to get last repo contents for task {self.task_id}"},
                self.ll.ERROR,
                500,
            )
            return None

        last_repo_contents = response[0]

        if tasks_diff_list:
            self.conn.request_line = (
                self.sql.repo_tasks_plan_hshs,
                {"id": tuple(tasks_diff_list), "act": "add"},
            )
            status, response = self.conn.send_request()
            if status is False:
                self._store_sql_error(response, self.ll.ERROR, 500)
                return None
            if not response:
                tasks_diff_add_hshs = set()
            else:
                tasks_diff_add_hshs = set(join_tuples(response))

            self.conn.request_line = (
                self.sql.repo_tasks_plan_hshs,
                {"id": tuple(tasks_diff_list), "act": "delete"},
            )
            status, response = self.conn.send_request()
            if status is False:
                self._store_sql_error(response, self.ll.ERROR, 500)
                return None
            if not response:
                tasks_diff_del_hshs = set()
            else:
                tasks_diff_del_hshs = set(join_tuples(response))

            if not tasks_diff_add_hshs and not tasks_diff_del_hshs:
                self._store_sql_error(
                    {
                        "Error": f"Failed to get task plan hashes for tasks {tasks_diff_list}"
                    },
                    self.ll.ERROR,
                    500,
                )
                return None
        else:
            tasks_diff_add_hshs = set()
            tasks_diff_del_hshs = set()

        task_base_repo_pkgs = (
            last_repo_pkgs - tasks_diff_del_hshs
        ) | tasks_diff_add_hshs
        task_current_repo_pkgs = (task_base_repo_pkgs - task_del_pkgs) | task_add_pkgs

        self.repo = {
            "base_repo_pkgs": tuple(task_base_repo_pkgs),
            "task_repo_pkgs": tuple(task_current_repo_pkgs),
            "task_add_pkgs": tuple(task_add_pkgs),
            "task_del_pkgs": tuple(task_del_pkgs),
            # 'last_repo_pkgs': tuple(last_repo_pkgs),
            "last_repo_contents": last_repo_contents,
            "tasks_diff_list": list(tasks_diff_list),
            # 'tasks_diff_add_hshs': tuple(tasks_diff_add_hshs),
            # 'tasks_diff_del_hshs': tuple(tasks_diff_add_hshs)
        }
        self.status = True
        return None

    def get(self):
        self.include_task_packages = self.args["include_task_packages"]
        self.build_task_repo()

        if not self.status:
            return self.error

        # create temporary table for packages hashaes
        self.conn.request_line = self.sql.create_tmp_hshs_table.format(
            table="tmpPkgHshs"
        )
        status, response = self.conn.send_request()
        if status is False:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error

        # insert hashes for packages into temporary table
        if self.include_task_packages:
            # use task_current_repo_pkgs
            self.conn.request_line = (
                self.sql.insert_into_tmp_hshs_table.format(table="tmpPkgHshs"),
                ({"pkghash": x} for x in self.repo["task_repo_pkgs"]),
            )
        else:
            # use task_base_repo_pkgs
            self.conn.request_line = (
                self.sql.insert_into_tmp_hshs_table.format(table="tmpPkgHshs"),
                ({"pkghash": x} for x in self.repo["base_repo_pkgs"]),
            )

        status, response = self.conn.send_request()
        if status is False:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error

        self.conn.request_line = self.sql.repo_packages_by_hshs.format(
            table="tmpPkgHshs"
        )
        status, response = self.conn.send_request()
        if status is False:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        if not response:
            if not response:
                self._store_sql_error(
                    {"Error": "Failed to get packages data from database"},
                    self.ll.ERROR,
                    500,
                )
                return self.error
        else:
            repo_pkgs = defaultdict(list)
            for el in response:
                if el[5] == 1:
                    repo_pkgs["SRPM"].append(
                        {
                            "name": el[0],
                            "version": el[1],
                            "release": el[2],
                            "filename": el[4],
                        }
                    )
                else:
                    repo_pkgs[el[3]].append(
                        {
                            "name": el[0],
                            "version": el[1],
                            "release": el[2],
                            "filename": el[4],
                        }
                    )

        # build final result
        res = {
            "task_id": self.task_id,
            "base_repository": {
                "name": self.repo["last_repo_contents"][0],
                "date": self.repo["last_repo_contents"][1].isoformat(),
                "tag": self.repo["last_repo_contents"][2],
            },
            "task_diff_list": self.repo["tasks_diff_list"],
            "archs": [],
        }

        for k, v in repo_pkgs.items():
            res["archs"].append({"arch": k, "packages": v})

        return res, 200


class TaskRepoState(APIWorker):
    """Builds package set state from task."""

    def __init__(self, connection: object, id: int, **kwargs) -> None:
        self.conn = connection
        self.args = kwargs
        self.sql = tasksql
        self.task_id = id
        self.repo = {}
        super().__init__()

    def check_task_id(self) -> bool:
        self.conn.request_line = self.sql.check_task.format(id=self.task_id)
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.INFO, 500)
            return False

        if response[0][0] == 0:
            return False
        return True

    def build_task_repo(self) -> tuple[int]:
        if not self.check_task_id():
            self._store_sql_error(
                {"Error": f"Non-existent task {self.task_id}"},
                self.ll.ERROR,
                404,
            )
            return None
        #  get task branch
        self.conn.request_line = self.sql.task_repo.format(id=self.task_id)
        status, response = self.conn.send_request()
        if status is False:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.repo
        if not response:
            self._store_sql_error(
                {"Error": f"Non-existent data for task {self.task_id}"},
                self.ll.ERROR,
                500,
            )
            return None
        task_repo = response[0][0]
        # get task state
        self.conn.request_line = self.sql.task_state.format(id=self.task_id)
        status, response = self.conn.send_request()
        if status is False:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.repo
        if not response:
            self._store_sql_error(
                {"Error": f"Non-existent data for task {self.task_id}"},
                self.ll.ERROR,
                500,
            )
            return None
        task_state = response[0][0]
        if task_state not in ("DONE", "EPERM", "TESTED", "FAILED"):
            self._store_error(
                {"Error": f"task state {task_state} not supported for data query"},
                self.ll.INFO,
                404,
            )
        # get subtask try, iteration and archs
        self.conn.request_line = self.sql.repo_task_content.format(id=self.task_id)
        status, response = self.conn.send_request()
        if status is False:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return None
        if not response:
            self._store_sql_error(
                {"Error": f"Non-existent data for task {self.task_id}"},
                self.ll.ERROR,
                500,
            )
            return None

        task_archs = set(("src", "noarch", "x86_64-i586"))
        task_try = 0
        task_iter = 0
        for el in response:
            task_archs.add(el[0])
            task_try = el[1]
            task_iter = el[2]
        #  get task plan
        task_tplan_hashes = set()
        for arch in task_archs:
            t = str(self.task_id) + str(task_try) + str(task_iter) + arch
            task_tplan_hashes.add(mmhash(t))
        # get task plan 'add' hashes
        self.conn.request_line = (
            self.sql.repo_single_task_plan_hshs,
            {"hshs": tuple(task_tplan_hashes), "act": "add"},
        )
        status, response = self.conn.send_request()
        if status is False:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return None
        if response:
            task_add_pkgs = set(join_tuples(response))
        else:
            task_add_pkgs = set()
        # get task plan 'delete' hashes
        self.conn.request_line = (
            self.sql.repo_single_task_plan_hshs,
            {"hshs": tuple(task_tplan_hashes), "act": "delete"},
        )
        status, response = self.conn.send_request()
        if status is False:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return None
        if response:
            task_del_pkgs = set(join_tuples(response))
        else:
            task_del_pkgs = set()
        # if no task plan found return an error
        if not task_add_pkgs and not task_del_pkgs:
            self._store_error(
                {
                    "Error": f"No plan found for task {self.task_id} in state {task_state} in DB"
                },
                self.ll.INFO,
                404,
            )
        # get task_diff list and latest repo package hashes
        if task_state == "DONE":
            # if task state is 'DONE' use last previous repo and applly all 'DONE' task chain on top of it
            # get task diff list
            self.conn.request_line = self.sql.repo_tasks_diff_list_before_task.format(
                id=self.task_id, repo=task_repo
            )
            status, response = self.conn.send_request()
            if status is False:
                self._store_sql_error(response, self.ll.ERROR, 500)
                return None

            tasks_diff_list = []
            if response:
                tasks_diff_list += {el[0] for el in response}
            # get latest repo before task hashes
            self.conn.request_line = self.sql.repo_last_repo_hashes_before_task.format(
                id=self.task_id, repo=task_repo
            )
            status, response = self.conn.send_request()
            if status is False:
                self._store_sql_error(response, self.ll.ERROR, 500)
                return None
            if not response:
                self._store_sql_error(
                    {
                        "Error": f"Failed to get last repo packages for task {self.task_id}"
                    },
                    self.ll.ERROR,
                    500,
                )
                return None

            last_repo_pkgs = set(join_tuples(response))
        else:
            # if task state is 'EPERM', 'TESTED' or 'FAILED' use latest repo and apply all 'DONE' on top of it
            self.conn.request_line = self.sql.repo_last_repo_tasks_diff_list.format(
                repo=task_repo
            )
            status, response = self.conn.send_request()
            if status is False:
                self._store_sql_error(response, self.ll.ERROR, 500)
                return None

            tasks_diff_list = []
            if response:
                tasks_diff_list += {el[0] for el in response}
            # get latest repo before task hashes
            self.conn.request_line = self.sql.repo_last_repo_hashes.format(
                repo=task_repo
            )
            status, response = self.conn.send_request()
            if status is False:
                self._store_sql_error(response, self.ll.ERROR, 500)
                return None
            if not response:
                self._store_sql_error(
                    {
                        "Error": f"Failed to get last repo packages for task {self.task_id}"
                    },
                    self.ll.ERROR,
                    500,
                )
                return None

            last_repo_pkgs = set(join_tuples(response))

        if tasks_diff_list:
            self.conn.request_line = (
                self.sql.repo_tasks_plan_hshs,
                {"id": tuple(tasks_diff_list), "act": "add"},
            )
            status, response = self.conn.send_request()
            if status is False:
                self._store_sql_error(response, self.ll.ERROR, 500)
                return None
            if not response:
                tasks_diff_add_hshs = set()
            else:
                tasks_diff_add_hshs = set(join_tuples(response))

            self.conn.request_line = (
                self.sql.repo_tasks_plan_hshs,
                {"id": tuple(tasks_diff_list), "act": "delete"},
            )
            status, response = self.conn.send_request()
            if status is False:
                self._store_sql_error(response, self.ll.ERROR, 500)
                return None
            if not response:
                tasks_diff_del_hshs = set()
            else:
                tasks_diff_del_hshs = set(join_tuples(response))

            if not tasks_diff_add_hshs and not tasks_diff_del_hshs:
                self._store_sql_error(
                    {
                        "Error": f"Failed to get task plan hashes for tasks {tasks_diff_list}"
                    },
                    self.ll.ERROR,
                    500,
                )
                return None
        else:
            tasks_diff_add_hshs = set()
            tasks_diff_del_hshs = set()

        task_base_repo_pkgs = (last_repo_pkgs - tasks_diff_del_hshs) | tasks_diff_add_hshs
        task_current_repo_pkgs = (task_base_repo_pkgs - task_del_pkgs) | task_add_pkgs

        self.status = True
        return tuple(task_current_repo_pkgs)
