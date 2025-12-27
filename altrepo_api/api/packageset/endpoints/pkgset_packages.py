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

from collections import namedtuple
from typing import Any

from altrepo_api.api.base import APIWorker
from ..sql import sql


class PackagesetPackages(APIWorker):
    """Retrieves package set packages information."""

    PkgMeta = namedtuple(
        "PkgMeta",
        [
            "hash",
            "name",
            "version",
            "release",
            "summary",
            "maintainers",
            "url",
            "license",
            "category",
            "archs",
            "acl_list",
        ],
    )

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        return True

    def _get_done_tasks(self) -> list[int]:
        """Get list of DONE tasks after last repository state."""
        response = self.send_sql_request(
            self.sql.get_done_tasks_after_last_repo.format(branch=self.branch)
        )
        if not self.sql_status or not response:
            return []
        return [row[0] for row in response]

    def _get_task_plan_hashes(self, task_ids: tuple[int, ...], action: str) -> set[int]:
        """Get package hashes from task plans for given action (add/delete)."""
        if not task_ids:
            return set()
        response = self.send_sql_request(
            self.sql.get_task_plan_hashes.format(task_ids=task_ids, action=action)
        )
        if not self.sql_status or not response:
            return set()
        return {row[0] for row in response}

    def _get_packages_with_done_tasks(
        self, sourcef: tuple[int, ...], archs: str
    ) -> tuple[Any, int]:
        """Get packages including changes from DONE tasks."""
        # get base package hashes from current repository
        response = self.send_sql_request(
            self.sql.get_repo_packages.format(
                branch=self.branch, src=sourcef, archs=archs
            )
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

        base_hashes = {row[0] for row in response}

        # get DONE tasks after last repo state
        done_tasks = self._get_done_tasks()
        if not done_tasks:
            # no DONE tasks, return base packages
            retval = [self.PkgMeta(*el)._asdict() for el in response]
            return {
                "request_args": self.args,
                "length": len(retval),
                "packages": retval,
                "done_tasks": [],
            }, 200

        task_ids = tuple(done_tasks)

        # get add and delete hashes from DONE tasks
        add_hashes = self._get_task_plan_hashes(task_ids, "add")
        del_hashes = self._get_task_plan_hashes(task_ids, "delete")

        # apply modifications: (base - delete) | add
        final_hashes = (base_hashes - del_hashes) | add_hashes

        if not final_hashes:
            return self.store_error(
                {
                    "message": "No packages after applying DONE tasks",
                    "args": self.args,
                }
            )

        # get packages by final hashes
        response = self.send_sql_request(
            self.sql.get_packages_by_hashes.format(
                branch=self.branch,
                hashes=tuple(final_hashes),
                src=sourcef,
                archs=archs,
            )
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

        retval = [self.PkgMeta(*el)._asdict() for el in response]
        return {
            "request_args": self.args,
            "length": len(retval),
            "packages": retval,
            "done_tasks": done_tasks,
        }, 200

    def get(self):
        self.pkg_type = self.args["package_type"]
        self.branch = self.args["branch"]
        self.archs = self.args["archs"]
        self.include_done_tasks = self.args.get("include_done_tasks", False)

        # ignore 'archs' argument if package type is "source" or "all"
        if self.pkg_type in ("source", "all"):
            archs = ""
        elif self.archs:
            if "noarch" not in self.archs:
                self.archs.append("noarch")
            archs = f"AND pkg_arch IN {tuple(self.archs)}"
        else:
            archs = ""

        depends_type_to_sql = {"source": (1,), "binary": (0,), "all": (1, 0)}
        sourcef = depends_type_to_sql[self.pkg_type]

        if self.include_done_tasks:
            return self._get_packages_with_done_tasks(sourcef, archs)

        response = self.send_sql_request(
            self.sql.get_repo_packages.format(
                branch=self.branch, src=sourcef, archs=archs
            )
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

        retval = [self.PkgMeta(*el)._asdict() for el in response]

        res = {"request_args": self.args, "length": len(retval), "packages": retval}
        return res, 200
