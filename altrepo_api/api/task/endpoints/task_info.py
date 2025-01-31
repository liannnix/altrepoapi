# ALTRepo API
# Copyright (C) 2021-2025  BaseALT Ltd

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
from typing import Any, NamedTuple, Optional, Union

from altrepo_api.utils import datetime_to_iso, mmhash, valid_task_id
from altrepo_api.api.base import APIWorker

from ..sql import sql


MAX_TRY_ITER = 1_000


class TaskInfo(APIWorker):
    """Get information about the task based on task ID.
    Otpionally uses task try and iteration parameters
    """

    def __init__(self, connection, id_, **kwargs) -> None:
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        self.task_id = id_
        self.task: dict[str, Any] = defaultdict(lambda: None, key=None)
        super().__init__()

    def check_task_id(self):
        if not valid_task_id(self.task_id):
            return False
        response = self.send_sql_request(self.sql.check_task.format(id=self.task_id))
        if not self.sql_status:
            return False

        return response[0][0] != 0

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        self.validation_results = []

        try_ = self.args["try"]
        iter_ = self.args["iteration"]

        if try_ is None and iter_ is None:
            # neither of 'try' or 'iteration' args is provided
            pass
        elif try_ is None or iter_ is None:
            self.validation_results.append(
                "Task try and iteration parameters should be both specified"
            )
        else:
            if try_ < 1 or try_ > MAX_TRY_ITER:
                self.validation_results.append(
                    f"task try argument should be in range 1 to {MAX_TRY_ITER}"
                )
            if iter_ < 1 or iter_ > MAX_TRY_ITER:
                self.validation_results.append(
                    f"task iteration argument should be in range 1 to {MAX_TRY_ITER}"
                )

        states = self.args["states"]
        valid_states = ("DONE", "EPERM", "TESTED")
        if states:
            for state in states:
                if state not in valid_states:
                    self.validation_results.append(f"Invalid task state '{state}'")

        return self.validation_results == []

    class TaskState(NamedTuple):
        task_id: int
        task_state: str
        task_changed: datetime
        task_runby: str
        task_depends: list[int]
        task_try: int
        task_testonly: int
        task_failearly: int
        task_shared: int
        task_message: str
        task_version: str
        task_prev: int
        task_eventlog_hash: list[int]

        def asdict(self) -> dict[str, Any]:
            res = {}
            for field in self._fields:
                if field == "task_changed":
                    res["last_changed"] = getattr(self, field)
                else:
                    res[field.removeprefix("task_")] = getattr(self, field)
            return res

    def _get_task_state(
        self, task_changed: Optional[datetime] = None
    ) -> Union[TaskState, None]:
        self.status = False

        if task_changed is None:
            response = self.send_sql_request(
                self.sql.task_state_last.format(id=self.task_id)
            )
        else:
            response = self.send_sql_request(
                self.sql.task_state_by_task_changed.format(
                    id=self.task_id, changed=task_changed
                )
            )

        if not self.sql_status:
            return None
        if not response:
            _ = self.store_error(
                {"Error": f"No data found in database for task '{self.task_id}'"},
            )
            return None

        self.status = True
        return self.TaskState(*response[0])

    def _get_task_rebuilds(self, try_iter: Optional[tuple[int, int]]):
        self.status = False
        # get task rebuilds
        if self.task_states:
            iterations_where_clause = self.sql.task_iterations_where_clause.format(
                id=self.task_id, states=self.task_states
            )
        else:
            iterations_where_clause = ""

        response = self.send_sql_request(
            self.sql.task_all_iterations.format(
                id=self.task_id, where_clause=iterations_where_clause
            )
        )
        if not self.sql_status:
            return None
        if not response:
            _ = self.store_error(
                {"Error": f"No data found in database for task '{self.task_id}'"}
            )
            return None

        self.task["rebuilds"] = {  # type: ignore
            (i[0], i[1]): {"subtasks": [], "changed": i[3]} for i in response
        }

        for ti in self.task["rebuilds"].keys():
            for el in response:
                if (el[0], el[1]) == ti:
                    self.task["rebuilds"][ti]["subtasks"].append(el[2])  # type: ignore

            self.task["rebuilds"][ti]["subtasks"] = sorted(
                list(set(self.task["rebuilds"][ti]["subtasks"]))
            )

        if try_iter:
            if try_iter not in self.task["rebuilds"]:
                _ = self.store_error(
                    {
                        "Error": f"No data found in database for task '{self.task_id}' with rebuild '{try_iter}'"
                    }
                )
                return None
        else:
            self.task["try"], self.task["iter"] = max(self.task["rebuilds"])

        self.status = True

    def _get_subtasks(
        self, task_changed: datetime
    ) -> Union[list[dict[str, Any]], None]:
        self.status = False

        response = self.send_sql_request(
            self.sql.task_subtasks_by_task_changed.format(
                id=self.task_id, changed=task_changed
            )
        )
        if not self.sql_status:
            return None
        if not response:
            if self.task["state"] != "NEW":
                _ = self.store_error(
                    {
                        "Error": f"No data found in database for task '{self.task_id}' on {task_changed}"
                    }
                )
                return None
            else:
                self.status = True
                return []

        self.status = True
        return [dict(zip(self.sql.task_subtasks_keys, r)) for r in response]

    def _get_iterations(
        self, task_changed: datetime
    ) -> Union[list[dict[str, Any]], None]:
        self.status = False

        response = self.send_sql_request(
            self.sql.task_iterations_by_task_changed.format(
                id=self.task_id, changed=task_changed
            )
        )
        if not self.sql_status:
            return None
        if not response:
            if self.task["state"] != "NEW":
                _ = self.store_error(
                    {
                        "Error": f"No data found in database for task '{self.task_id}' on {task_changed}"
                    }
                )
                return None
            else:
                self.status = True
                return []

        self.status = True
        return [dict(zip(self.sql.task_iterations_keys, r)) for r in response]

    def _get_task_plan(self, iterations: list[dict[str, Any]]) -> None:
        self.status = False

        class PkgInfo(NamedTuple):
            name: str
            version: str
            release: str
            filename: str
            arch: str

        # collect archs from task iterations
        archs = set(("src", "noarch", "x86_64-i586"))
        [archs.add(x["subtask_arch"]) for x in iterations]
        self.task["archs"] = tuple(archs)

        for arch in self.task["archs"]:
            t = (
                str(self.task_id)
                + str(self.task["try"])
                + str(self.task["iter"])
                + arch
            )
            self.task["tplan_hashes"][arch] = mmhash(t)

        response = self.send_sql_request(
            self.sql.task_plan_packages.format(
                action="add",
                hshs=tuple([x for x in self.task["tplan_hashes"].values()]),
            )
        )
        if not self.sql_status:
            return None

        for el in response:
            if el[6] == 1:
                self.task["plan"]["add"]["src"][el[0]] = PkgInfo(*el[1:6])._asdict()
            else:
                self.task["plan"]["add"]["bin"][el[0]] = PkgInfo(*el[1:6])._asdict()

        response = self.send_sql_request(
            self.sql.task_plan_packages.format(
                action="delete",
                hshs=tuple([x for x in self.task["tplan_hashes"].values()]),
            )
        )
        if not self.sql_status:
            return None

        for el in response:
            if el[6] == 1:
                self.task["plan"]["del"]["src"][el[0]] = PkgInfo(*el[1:6])._asdict()
            else:
                self.task["plan"]["del"]["bin"][el[0]] = PkgInfo(*el[1:6])._asdict()

        src_pkg_hashes_not_in_plan = [
            hsh
            for hsh in {
                el["titer_srcrpm_hash"]
                for el in iterations
                if el["titer_srcrpm_hash"] != 0
            }
            if hsh not in self.task["plan"]["add"]["src"].keys()
        ]

        if src_pkg_hashes_not_in_plan:
            self.logger.warning(
                f"Found source packages missing from plan!\nTask: {self.task_id},"
                f" hashes: {src_pkg_hashes_not_in_plan}"
            )

        self.status = True

    def _get_task_approvals(self):
        self.status = False

        response = self.send_sql_request(
            self.sql.task_approvals.format(id=self.task_id)
        )
        if not self.sql_status:
            return None

        for subtask in self.task["subtasks"]:
            self.task["subtasks"][subtask].update({"approvals": []})

        if response:
            task_approvals = []
            tapp_keys = ("id", "date", "type", "name", "message", "revoked")

            for i in range(len(response)):
                task_approvals.append(
                    dict(
                        [
                            (tapp_keys[j], response[i][0][j])
                            for j in range(len(response[i][0]))
                        ]
                    )
                )

            for subtask in self.task["subtasks"]:
                self.task["subtasks"][subtask]["approvals"] = [
                    x for x in task_approvals if x["id"] == subtask
                ]

                for tapp in self.task["subtasks"][subtask]["approvals"]:
                    tapp["date"] = datetime_to_iso(tapp["date"])

        self.status = True

    def get(self):
        self.task_try = self.args["try"]
        self.task_iter = self.args["iteration"]
        self.task_states = self.args["states"]

        self.task = {"id": self.task_id, "try": self.task_try, "iter": self.task_iter}
        if self.task_try is not None and self.task_iter is not None:
            try_iter = (self.task_try, self.task_iter)
        else:
            try_iter = None

        # task structure init
        self.task["tplan_hashes"] = {}

        self.task["plan"] = {
            "add": {"src": {}, "bin": {}},
            "del": {"src": {}, "bin": {}},
        }

        # get task owner and repo
        response = self.send_sql_request(
            self.sql.task_repo_owner.format(id=self.task_id)
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {"Error": f"No data found in database for task '{self.task_id}'"}
            )

        self.task["branch"] = response[0][0]
        self.task["user"] = response[0][1]

        # get task rebuilds
        self._get_task_rebuilds(try_iter)
        if not self.status:
            return self.error

        task_changed = (
            self.task["rebuilds"][try_iter]["changed"]
            if try_iter == (self.task["try"], self.task["iter"])
            else None
        )

        # get task state
        task_state = self._get_task_state(task_changed)
        if not self.status or task_state is None:
            return self.error

        task_changed = task_state.task_changed

        self.task.update(**task_state.asdict())

        # return here for deleted task
        if task_state.task_state == "DELETED":
            self.task["rebuilds"] = [
                (str(x[0]) + "." + str(x[1]))
                for x in sorted(self.task["rebuilds"].keys())
            ]
            self.task["subtasks"] = []

            return self.task, 200

        # get subtasks
        subtasks = self._get_subtasks(task_changed)
        if not self.status or subtasks is None:
            return self.error

        # get iterations
        iterations = self._get_iterations(task_changed)
        if not self.status or iterations is None:
            return self.error

        self.task["subtasks"] = {x["subtask_id"]: {} for x in subtasks}

        # process task plan only for tasks that should have it
        if task_state.task_state in ("DONE", "EPERM", "TESTED") or try_iter is not None:
            self._get_task_plan(iterations)
            if not self.status:
                return self.error

        # get task approvals
        self._get_task_approvals()
        if not self.status:
            return self.error

        # build result
        for subtask in self.task["subtasks"].keys():
            contents: dict[str, Any] = {"archs": []}

            for sub_ in subtasks:
                if sub_["subtask_id"] == subtask:
                    contents["last_changed"] = datetime_to_iso(sub_["subtask_changed"])
                    contents["userid"] = sub_["subtask_userid"]
                    contents["dir"] = sub_["subtask_dir"]
                    contents["package"] = sub_["subtask_package"]
                    contents["type"] = sub_["subtask_type"]
                    contents["pkg_from"] = sub_["subtask_pkg_from"]
                    contents["sid"] = sub_["subtask_sid"]
                    contents["tag_author"] = sub_["subtask_tag_author"]
                    contents["tag_id"] = sub_["subtask_tag_id"]
                    contents["tag_name"] = sub_["subtask_tag_name"]
                    contents["srpm"] = sub_["subtask_srpm"]
                    contents["srpm_name"] = sub_["subtask_srpm_name"]
                    contents["srpm_evr"] = sub_["subtask_srpm_evr"]
                    break

            for iter_ in iterations:
                if iter_["subtask_id"] == subtask and iter_["subtask_arch"] == "x86_64":
                    if (
                        iter_["titer_srcrpm_hash"] != 0
                        and iter_["titer_srcrpm_hash"]
                        in self.task["plan"]["add"]["src"]
                    ):
                        contents["source_package"] = self.task["plan"]["add"]["src"][
                            iter_["titer_srcrpm_hash"]
                        ]
                    else:
                        contents["source_package"] = {}  # type: ignore
                    break

            for iter_ in iterations:
                if iter_["subtask_id"] == subtask:
                    iteration = {}
                    iteration["last_changed"] = datetime_to_iso(iter_["titer_ts"])
                    iteration["arch"] = iter_["subtask_arch"]
                    iteration["status"] = iter_["titer_status"]
                    contents["archs"].append(iteration)

            self.task["subtasks"][subtask].update(contents)

        self.task["rebuilds"] = [
            (str(x[0]) + "." + str(x[1]))
            for x in sorted(self.task["rebuilds"].keys(), reverse=True)
        ]

        subtasks = []

        for subtask, contents in self.task["subtasks"].items():
            subtask_dict = {"subtask_id": subtask}
            subtask_dict.update(contents)
            subtasks.append(subtask_dict)

        self.task["subtasks"] = subtasks

        self.task["plan"]["add"]["src"] = [  # type: ignore
            x for x in self.task["plan"]["add"]["src"].values()
        ]
        self.task["plan"]["add"]["bin"] = [  # type: ignore
            x for x in self.task["plan"]["add"]["bin"].values()
        ]
        self.task["plan"]["del"]["src"] = [  # type: ignore
            x for x in self.task["plan"]["del"]["src"].values()
        ]
        self.task["plan"]["del"]["bin"] = [  # type: ignore
            x for x in self.task["plan"]["del"]["bin"].values()
        ]

        del self.task["tplan_hashes"]

        return self.task, 200
