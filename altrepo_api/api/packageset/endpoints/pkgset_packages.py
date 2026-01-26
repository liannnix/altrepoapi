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

from typing import NamedTuple

from altrepo_api.api.base import APIWorker
from altrepo_api.utils import make_tmp_table_name
from ..sql import sql


class PackagesetPackages(APIWorker):
    """Retrieves package set packages information."""

    class PkgMeta(NamedTuple):
        hash: int
        name: str
        version: str
        release: str
        summary: str
        maintainers: list[str]
        url: str
        license: str
        category: str
        archs: str
        acl_list: list[str]

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        return True

    def _get_done_tasks(self, branch: str) -> list[int]:
        """Get list of DONE tasks after last repository state."""

        self.status = False

        response = self.send_sql_request(
            self.sql.get_done_tasks_after_last_repo.format(branch=branch)
        )
        if not self.sql_status:
            return []

        self.status = True
        return [row[0] for row in response]

    def _get_task_plan_hashes(self, task_ids: list[int], action: str) -> set[int]:
        """Get package hashes from task plans for given action (add/delete)."""

        self.status = False

        response = self.send_sql_request(
            self.sql.get_task_plan_hashes.format(task_ids=task_ids, action=action)
        )
        if not self.sql_status:
            return set()

        self.status = True
        return {row[0] for row in response}

    def get(self):
        pkg_type = self.args["package_type"]
        branch = self.args["branch"]
        archs = self.args["archs"]
        include_done_tasks = self.args.get("include_done_tasks", False)

        # ignore 'archs' argument if package type is "source" or "all"
        if pkg_type in ("source", "all"):
            archs = ""
        elif archs:
            if "noarch" not in archs:
                archs.append("noarch")
            archs = f"AND pkg_arch IN {tuple(archs)}"
        else:
            archs = ""

        depends_type_to_sql = {"source": (1,), "binary": (0,), "all": (1, 0)}
        sourcef = depends_type_to_sql[pkg_type]

        # get base package hashes from current repository
        response = self.send_sql_request(
            self.sql.get_repo_packages.format(branch=branch, src=sourcef, archs=archs)
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {
                    "message": "No data found in database for given parameters",
                    "args": self.args,
                }
            )

        # try to collect DONE tasks after latest branch commit
        done_tasks = []
        if include_done_tasks:
            # get DONE tasks after last repo state
            done_tasks = self._get_done_tasks(branch)
            if not self.status:
                return self.error

        # no `include_done_tasks` where provided or not DONE tasks found after
        # lates branh commit
        if not done_tasks:
            packages = [self.PkgMeta(*el)._asdict() for el in response]

            res = {
                "request_args": self.args,
                "length": len(packages),
                "packages": packages,
                "done_tasks": done_tasks,
            }
            return res, 200

        # get base package hashes from current repository state
        base_hashes = {row[0] for row in response}

        # get add and delete hashes from DONE tasks
        add_hashes = self._get_task_plan_hashes(done_tasks, "add")
        if not self.status:
            return self.error
        del_hashes = self._get_task_plan_hashes(done_tasks, "delete")
        if not self.status:
            return self.error

        # apply modifications: (base - delete) | add
        final_hashes = (base_hashes - del_hashes) | add_hashes

        if not final_hashes:
            return self.store_error(
                {
                    "message": "No packages after applying DONE tasks",
                    "args": self.args,
                }
            )

        # get packages by combined hashes of last repo state and done tasks
        tmp_table = make_tmp_table_name("pkg_hshs")
        response = self.send_sql_request(
            self.sql.get_packages_by_tmp_table.format(
                branch=branch,
                table=tmp_table,
                src=sourcef,
                archs=archs,
            ),
            external_tables=[
                {
                    "name": tmp_table,
                    "structure": [
                        ("pkg_hash", "UInt64"),
                    ],
                    "data": [{"pkg_hash": pkg_hash} for pkg_hash in final_hashes],
                }
            ],
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {
                    "message": "No packages found for computed hashes",
                    "args": self.args,
                }
            )

        packages = [self.PkgMeta(*el)._asdict() for el in response]

        return {
            "request_args": self.args,
            "length": len(packages),
            "packages": packages,
            "done_tasks": done_tasks,
        }, 200
