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

from collections import defaultdict, namedtuple

from altrepo_api.utils import datetime_to_iso, mmhash

from altrepo_api.api.base import APIWorker
from ..sql import sql


class TaskInfo(APIWorker):
    """Get information about the task based on task ID.
    Otpionally uses task try and iteration parameters
    """

    def __init__(self, connection, id_, **kwargs) -> None:
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        self.task_id = id_
        self.task = defaultdict(lambda: None, key=None)
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

        if self.args["try"] is not None and self.args["iteration"] is not None:
            if self.args["try"] > 0 and self.args["iteration"] > 0:
                pass
            else:
                self.validation_results.append(
                    f"Task try and iteration parameters should be both greater than 0"
                )
        elif self.args["try"] is None and self.args["iteration"] is None:
            pass
        else:
            self.validation_results.append(
                f"Task try and iteration parameters should be both specified"
            )

        if self.validation_results != []:
            return False
        else:
            return True

    def build_task_state(self):
        self.task = {"id": self.task_id, "try": self.task_try, "iter": self.task_iter}
        if self.task_try is not None and self.task_iter is not None:
            try_iter = (self.task_try, self.task_iter)
        else:
            try_iter = None

        self.conn.request_line = self.sql.task_repo_owner.format(id=self.task_id)
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return None
        if not response:
            self._store_sql_error(
                {"Error": f"No data found in database for task '{self.task_id}'"},
                self.ll.INFO,
                404,
            )
            return None

        self.task["branch"] = response[0][0]
        self.task["user"] = response[0][1]

        self.conn.request_line = self.sql.task_all_iterations.format(id=self.task_id)
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return None
        if not response:
            self._store_sql_error(
                {"Error": f"No data found in database for task '{self.task_id}'"},
                self.ll.INFO,
                404,
            )
            return None

        self.task["rebuilds"] = {
            (i[0], i[1]): {"subtasks": [], "changed": i[3]} for i in response
        }
        for ti in self.task["rebuilds"].keys():
            for el in response:
                if (el[0], el[1]) == ti:
                    self.task["rebuilds"][ti]["subtasks"].append(el[2])
            self.task["rebuilds"][ti]["subtasks"] = sorted(
                list(set(self.task["rebuilds"][ti]["subtasks"]))
            )

        if try_iter:
            if try_iter not in self.task["rebuilds"]:
                self._store_sql_error(
                    {
                        "Error": f"No data found in database for task '{self.task_id}' with rebuild '{try_iter}'"
                    },
                    self.ll.INFO,
                    404,
                )
                return None
        else:
            try_iter = max(self.task["rebuilds"])
            self.task["try"], self.task["iter"] = try_iter

        task_changed = self.task["rebuilds"][try_iter]["changed"]
        self.task["subtasks"] = {
            x: {} for x in self.task["rebuilds"][try_iter]["subtasks"]
        }

        self.conn.request_line = self.sql.task_state_by_task_changed.format(
            id=self.task_id, changed=task_changed
        )
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return None
        if not response:
            self._store_sql_error(
                {
                    "Error": f"No data found in database for task '{self.task_id}' with rebuild '{try_iter}'"
                },
                self.ll.INFO,
                404,
            )
            return None

        self.task["state_raw"] = dict(zip(self.sql.task_state_keys, response[0]))

        self.conn.request_line = self.sql.task_subtasks_by_task_changed.format(
            id=self.task_id, changed=task_changed
        )
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return None
        if not response:
            self._store_sql_error(
                {
                    "Error": f"No data found in database for task '{self.task_id}' with rebuild '{try_iter}'"
                },
                self.ll.INFO,
                404,
            )
            return None

        self.task["subtasks_raw"] = [
            dict(zip(self.sql.task_subtasks_keys, r)) for r in response
        ]

        self.conn.request_line = self.sql.task_iterations_by_task_changed.format(
            id=self.task_id, changed=task_changed
        )
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return None
        if not response:
            self._store_sql_error(
                {
                    "Error": f"No data found in database for task '{self.task_id}' with rebuild '{try_iter}'"
                },
                self.ll.INFO,
                404,
            )
            return None

        self.task["iterations_raw"] = [
            dict(zip(self.sql.task_iterations_keys, r)) for r in response
        ]

        self.task["subtasks"] = {x["subtask_id"]: {} for x in self.task["subtasks_raw"]}

        self.task["archs"] = set(("src", "noarch", "x86_64-i586"))
        [self.task["archs"].add(x["subtask_arch"]) for x in self.task["iterations_raw"]]
        self.task["archs"] = tuple(self.task["archs"])

        self.task["tplan_hashes"] = {}
        for arch in self.task["archs"]:
            t = (
                str(self.task_id)
                + str(self.task["try"])
                + str(self.task["iter"])
                + arch
            )
            self.task["tplan_hashes"][arch] = mmhash(t)

        self.task["plan"] = {
            "add": {"src": {}, "bin": {}},
            "del": {"src": {}, "bin": {}},
        }

        self.conn.request_line = self.sql.task_plan_packages.format(
            action="add", hshs=tuple([x for x in self.task["tplan_hashes"].values()])
        )
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return None

        PkgInfo = namedtuple(
            "PkgInfo", ("name", "version", "release", "filename", "arch")
        )

        for el in response:
            if el[6] == 1:
                self.task["plan"]["add"]["src"][el[0]] = PkgInfo(*el[1:6])._asdict()
            else:
                self.task["plan"]["add"]["bin"][el[0]] = PkgInfo(*el[1:6])._asdict()

        self.conn.request_line = self.sql.task_plan_packages.format(
            action="delete", hshs=tuple([x for x in self.task["tplan_hashes"].values()])
        )
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return None

        for el in response:
            if el[6] == 1:
                self.task["plan"]["del"]["src"][el[0]] = PkgInfo(*el[1:6])._asdict()
            else:
                self.task["plan"]["del"]["bin"][el[0]] = PkgInfo(*el[1:6])._asdict()

        # FIXME: Add warning message for tasks with inconsistent plan
        src_pkg_hashes_not_in_plan = [
            hsh
            for hsh in {
                el["titer_srcrpm_hash"]
                for el in self.task["iterations_raw"]
                if el["titer_srcrpm_hash"] != 0
            }
            if hsh not in self.task["plan"]["add"]["src"].keys()
        ]

        if src_pkg_hashes_not_in_plan:
            self.logger.warning(
                f"Found source packages missing from plan!\nTask: {self.task_id}, hashes: {src_pkg_hashes_not_in_plan}"
            )

        self.conn.request_line = self.sql.task_approvals.format(id=self.task_id)
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
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

        self.task["state"] = self.task["state_raw"]["task_state"]
        self.task["runby"] = self.task["state_raw"]["task_runby"]
        self.task["depends"] = self.task["state_raw"]["task_depends"]
        self.task["testonly"] = self.task["state_raw"]["task_testonly"]
        self.task["failearly"] = self.task["state_raw"]["task_failearly"]
        self.task["shared"] = self.task["state_raw"]["task_shared"]
        self.task["message"] = self.task["state_raw"]["task_message"]
        self.task["version"] = self.task["state_raw"]["task_version"]
        self.task["prev"] = self.task["state_raw"]["task_prev"]
        self.task["last_changed"] = datetime_to_iso(
            self.task["state_raw"]["task_changed"]
        )

        for subtask in self.task["subtasks"].keys():
            contents = {"archs": []}
            for sub_ in self.task["subtasks_raw"]:
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
            for iter_ in self.task["iterations_raw"]:
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
                        contents["source_package"] = {}
                    break
            for iter_ in self.task["iterations_raw"]:
                if iter_["subtask_id"] == subtask:
                    iteration = {}
                    iteration["last_changed"] = datetime_to_iso(iter_["titer_ts"])
                    iteration["arch"] = iter_["subtask_arch"]
                    iteration["status"] = iter_["titer_status"]
                    contents["archs"].append(iteration)

            self.task["subtasks"][subtask].update(contents)

        self.task["all_rebuilds"] = [
            (str(x[0]) + "." + str(x[1])) for x in sorted(self.task["rebuilds"].keys())
        ]

        self.task["rebuilds"] = self.task["all_rebuilds"]

        subtasks = []
        for subtask, contents in self.task["subtasks"].items():
            subtask_dict = {"subtask_id": subtask}
            subtask_dict.update(contents)
            subtasks.append(subtask_dict)
        self.task["subtasks"] = subtasks

        self.task["plan"]["add"]["src"] = [
            x for x in self.task["plan"]["add"]["src"].values()
        ]
        self.task["plan"]["add"]["bin"] = [
            x for x in self.task["plan"]["add"]["bin"].values()
        ]
        self.task["plan"]["del"]["src"] = [
            x for x in self.task["plan"]["del"]["src"].values()
        ]
        self.task["plan"]["del"]["bin"] = [
            x for x in self.task["plan"]["del"]["bin"].values()
        ]

        del self.task["iterations_raw"]
        del self.task["subtasks_raw"]
        del self.task["state_raw"]
        del self.task["tplan_hashes"]

        self.status = True
        return None

    def get(self):
        self.task_try = self.args["try"]
        self.task_iter = self.args["iteration"]
        self.build_task_state()

        if self.status:
            return self.task, 200
        else:
            return self.error
