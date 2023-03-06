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

from altrepo_api.utils import join_tuples, mmhash
from altrepo_api.api.base import APIWorker
from ..sql import sql


class TaskRepoState(APIWorker):
    """Builds package set state from task."""

    def __init__(self, connection, id: int, **kwargs) -> None:
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        self.task_id: int = id
        self.task_repo: str = ""
        self.task_diff_list: list[int] = list()
        self.task_add_pkgs: tuple[int, ...] = tuple()
        self.task_del_pkgs: tuple[int, ...] = tuple()
        self.task_repo_pkgs: tuple[int, ...] = tuple()
        self.task_base_repo_pkgs: tuple[int, ...] = tuple()
        self.have_plan: bool = False
        super().__init__()

    def check_task_id(self):
        response = self.send_sql_request(self.sql.check_task.format(id=self.task_id))
        if not self.sql_status:
            return False

        return response[0][0] != 0

    def build_task_repo(self, keep_artefacts: bool) -> None:
        if not self.check_task_id():
            _ = self.store_error({"Error": f"Non-existent task {self.task_id}"})
            return None

        #  get task branch
        response = self.send_sql_request(self.sql.task_repo.format(id=self.task_id))
        if not self.sql_status:
            return None
        if not response:
            _ = self.store_error(
                {"Error": f"Non-existent data for task {self.task_id}"},
                self.LL.ERROR,
                500,
            )
            return None

        self.task_repo = response[0][0]  # type: ignore

        # get task state
        response = self.send_sql_request(self.sql.task_state.format(id=self.task_id))
        if not self.sql_status:
            return None
        if not response:
            _ = self.store_error(
                {"Error": f"Non-existent data for task {self.task_id}"},
                self.LL.ERROR,
                500,
            )
            return None

        task_state = response[0][0]  # type: ignore

        if task_state not in ("DONE", "EPERM", "TESTED", "FAILED"):
            _ = self.store_error(
                {"Error": f"task state {task_state} not supported for data query"}
            )
            return None

        # get subtask try, iteration and archs
        response = self.send_sql_request(
            self.sql.repo_task_content.format(id=self.task_id)
        )
        if not self.sql_status:
            return None
        if not response:
            _ = self.store_error(
                {"Error": f"Non-existent data for task {self.task_id}"},
                self.LL.ERROR,
                500,
            )
            return None

        task_archs = set(("src", "noarch", "x86_64-i586"))
        task_try = 0
        task_iter = 0

        for el in response:
            task_archs.add(el[0])  # type: ignore
            task_try = el[1]
            task_iter = el[2]  # type: ignore

        #  get task plan
        task_tplan_hashes = set()

        for arch in task_archs:
            t = str(self.task_id) + str(task_try) + str(task_iter) + arch
            task_tplan_hashes.add(mmhash(t))

        # get task plan 'add' hashes
        response = self.send_sql_request(
            (
                self.sql.repo_single_task_plan_hshs,
                {"hshs": tuple(task_tplan_hashes), "act": "add"},
            )
        )
        if not self.sql_status:
            return None

        if response:
            task_add_pkgs = set(join_tuples(response))  # type: ignore
        else:
            task_add_pkgs = set()

        # get task plan 'delete' hashes
        response = self.send_sql_request(
            (
                self.sql.repo_single_task_plan_hshs,
                {"hshs": tuple(task_tplan_hashes), "act": "delete"},
            )
        )
        if not self.sql_status:
            return None

        if response:
            task_del_pkgs = set(join_tuples(response))  # type: ignore
        else:
            task_del_pkgs = set()

        # if no task plan found return an error if task not in 'FAILED' state
        if not task_add_pkgs and not task_del_pkgs:
            if task_state in ("FAILED", "POSTPONED"):
                self.have_plan = False
            else:
                _ = self.store_error(
                    {
                        "Error": f"No plan found for task {self.task_id} in state {task_state} in DB"
                    }
                )
                return None
        else:
            self.have_plan = True

        # get task_diff list and latest repo package hashes
        if task_state == "DONE":
            # if task state is 'DONE' use last previous repo and applly all 'DONE' task chain on top of it
            # get task diff list
            response = self.send_sql_request(
                self.sql.repo_tasks_diff_list_before_task.format(
                    id=self.task_id, repo=self.task_repo
                )
            )
            if not self.sql_status:
                return None

            tasks_diff_list = []

            if response:
                tasks_diff_list += {el[0] for el in response}

            # get latest repo before task hashes
            response = self.send_sql_request(
                self.sql.repo_last_repo_hashes_before_task.format(
                    id=self.task_id, repo=self.task_repo
                )
            )
            if not self.sql_status:
                return None
            if not response:
                _ = self.store_error(
                    {
                        "Error": f"Failed to get last repo packages for task {self.task_id}"
                    },
                    self.LL.ERROR,
                    500,
                )
                return None

            last_repo_pkgs = set(join_tuples(response))  # type: ignore
        else:
            # if task state is 'EPERM', 'TESTED', 'POSTPONED' or 'FAILED'
            # use latest repo and apply all 'DONE' on top of it
            response = self.send_sql_request(
                self.sql.repo_last_repo_tasks_diff_list.format(repo=self.task_repo)
            )
            if not self.sql_status:
                return None

            tasks_diff_list = []

            if response:
                tasks_diff_list += {el[0] for el in response}

            # get latest repo before task hashes
            response = self.send_sql_request(
                self.sql.repo_last_repo_hashes.format(repo=self.task_repo)
            )
            if not self.sql_status:
                return None
            if not response:
                _ = self.store_error(
                    {
                        "Error": f"Failed to get last repo packages for task {self.task_id}"
                    },
                    self.LL.ERROR,
                    500,
                )
                return None

            last_repo_pkgs = set(join_tuples(response))  # type: ignore

        if tasks_diff_list:
            self.task_diff_list = tasks_diff_list

            response = self.send_sql_request(
                (
                    self.sql.repo_tasks_plan_hshs,
                    {"id": tuple(tasks_diff_list), "act": "add"},
                )
            )
            if not self.sql_status:
                return None

            if not response:
                tasks_diff_add_hshs = set()
            else:
                tasks_diff_add_hshs = set(join_tuples(response))  # type: ignore

            response = self.send_sql_request(
                (
                    self.sql.repo_tasks_plan_hshs,
                    {"id": tuple(tasks_diff_list), "act": "delete"},
                )
            )
            if not self.sql_status:
                return None

            if not response:
                tasks_diff_del_hshs = set()
            else:
                tasks_diff_del_hshs = set(join_tuples(response))  # type: ignore

            if not tasks_diff_add_hshs and not tasks_diff_del_hshs:
                _ = self.store_error(
                    {
                        "Error": f"Failed to get task plan hashes for tasks {tasks_diff_list}"
                    },
                    self.LL.ERROR,
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

        if keep_artefacts:
            self.task_add_pkgs = tuple(task_add_pkgs)
            self.task_del_pkgs = tuple(task_del_pkgs)
            self.task_base_repo_pkgs = tuple(task_base_repo_pkgs)

        self.task_repo_pkgs = tuple(task_current_repo_pkgs)
        self.status = True
        return None


class TaskRepo(APIWorker):
    """Builds package set state from task."""

    def __init__(self, connection, id, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        self.task_id = id
        self.repo = TaskRepoState(self.conn, self.task_id)
        self.last_repo_contents = []
        super().__init__()

    def check_task_id(self):
        response = self.send_sql_request(self.sql.check_task.format(id=self.task_id))
        if not self.sql_status:
            return False

        return response[0][0] != 0

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        return True

    def build_task_repo(self):
        if not self.check_task_id():
            _ = self.store_error({"Error": f"Non-existent task {self.task_id}"})
            return None

        self.repo.build_task_repo(keep_artefacts=True)

        if not self.repo.status:
            return self.repo.error

        response = self.send_sql_request(
            self.sql.repo_last_repo_content.format(
                id=self.task_id, repo=self.repo.task_repo
            )
        )
        if not self.sql_status:
            return None
        if not response:
            _ = self.store_error(
                {"Error": f"Failed to get last repo contents for task {self.task_id}"},
                self.LL.ERROR,
                500,
            )
            return None

        self.last_repo_contents = response[0]  # type: ignore

        self.status = True
        return None

    def get(self):
        self.include_task_packages = self.args["include_task_packages"]
        self.build_task_repo()

        if not self.status:
            return self.error

        # create temporary table for packages hashaes
        _ = self.send_sql_request(
            self.sql.create_tmp_hshs_table.format(table="tmpPkgHshs")
        )
        if not self.sql_status:
            return self.error

        # insert hashes for packages into temporary table
        if self.include_task_packages:
            # use task_current_repo_pkgs
            request_line = (
                self.sql.insert_into_tmp_hshs_table.format(table="tmpPkgHshs"),
                ({"pkghash": x} for x in self.repo.task_repo_pkgs),
            )
        else:
            # use task_base_repo_pkgs
            request_line = (
                self.sql.insert_into_tmp_hshs_table.format(table="tmpPkgHshs"),
                ({"pkghash": x} for x in self.repo.task_base_repo_pkgs),
            )

        _ = self.send_sql_request(request_line)
        if not self.sql_status:
            return self.error

        response = self.send_sql_request(
            self.sql.repo_packages_by_hshs.format(table="tmpPkgHshs")
        )
        if not self.sql_status:
            return self.error

        repo_pkgs = defaultdict(list)

        if not response:
            return self.store_error(
                {"Error": "Failed to get packages data from database"},
                self.LL.ERROR,
                500,
            )
        else:
            for el in response:
                if el[5] == 1:  # type: ignore
                    repo_pkgs["SRPM"].append(
                        {
                            "name": el[0],
                            "version": el[1],
                            "release": el[2],  # type: ignore
                            "filename": el[4],  # type: ignore
                        }
                    )
                else:
                    repo_pkgs[el[3]].append(  # type: ignore
                        {
                            "name": el[0],
                            "version": el[1],
                            "release": el[2],  # type: ignore
                            "filename": el[4],  # type: ignore
                        }
                    )

        # build final result
        res = {
            "task_id": self.task_id,
            "base_repository": {
                "name": self.last_repo_contents[0],
                "date": self.last_repo_contents[1].isoformat(),  # type: ignore
                "tag": self.last_repo_contents[2],
            },
            "task_diff_list": self.repo.task_diff_list,
            "archs": [],
        }

        for k, v in repo_pkgs.items():
            res["archs"].append({"arch": k, "packages": v})

        return res, 200


class LastRepoStateFromTask(APIWorker):
    """Retrieves last branch state including all done tasks."""

    def __init__(self, connection, branch: str, **kwargs) -> None:
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        self.branch = branch
        self.task_repo_pkgs = None

    def build_repo_state(self) -> None:
        last_task_id = 0

        # get list of done tasks from last branch state
        response = self.send_sql_request(
            self.sql.repo_last_repo_tasks_diff_list.format(repo=self.branch)
        )
        if not self.sql_status:
            return None
        if not response:
            # if no tasks found from last repo state return 'None'
            self.status = True
            return None

        last_task_id = int(response[0][0])  # type: ignore

        tr = TaskRepoState(self.conn, last_task_id)
        tr.build_task_repo(keep_artefacts=False)

        # something gone wrong during task repo build
        if not tr.status:
            self.error = tr.error
            self.status = False
            return None

        # return latest repo state
        self.status = True
        self.task_repo_pkgs = tr.task_repo_pkgs
        return None
