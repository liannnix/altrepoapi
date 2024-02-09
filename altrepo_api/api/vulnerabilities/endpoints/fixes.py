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

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Union, Any, Iterable, NamedTuple

from altrepo_api.api.base import APIWorker
from altrepo_api.api.misc import lut
from altrepo_api.libs.librpm_functions import compare_versions, VersionCompareResult
from altrepo_api.utils import make_tmp_table_name, sort_branches

from .common import (
    Errata,
    PackageVersion,
    get_errata_by_cve_id,
)
from ..sql import sql


@dataclass
class Task:
    id: int
    branch: str
    package: str


@dataclass
class TaskHistory:
    id: int
    prev: int
    branch: str
    changed: datetime


@dataclass
class PackageMeta:
    pkghash: str
    name: str
    branch: str
    version: str
    release: str


@dataclass
class PackageScheme(PackageMeta):
    errata_id: str
    task_id: int
    subtask_id: int
    task_state: str
    last_version: Union[PackageMeta, None] = None

    def asdict(self) -> dict[str, Any]:
        return asdict(self)


class VulnFixes(APIWorker):
    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()
        self.erratas: list[Errata] = []
        self.packages_versions: dict[tuple[str, str], PackageVersion] = {}
        self.erratas_packages: dict[tuple[str, str], PackageScheme] = {}

    @staticmethod
    def _get_package_names(
        errata_packages: dict[tuple[str, str], PackageScheme]
    ) -> dict[str, list[tuple[str, int]]]:
        """
        Get a dictionary where the key is the package name
        and the value is a list of branches and tasks.
        """
        package_names: dict[str, list[tuple[str, int]]] = {}
        for el in errata_packages.values():
            package_names.setdefault(el.name, []).append((el.branch, el.task_id))
        return package_names

    @staticmethod
    def _get_pkgs_branches(
        pkg_names: dict[str, list[tuple[str, int]]]
    ) -> dict[str, set[str]]:

        pkgs_branches: dict[str, set[str]] = {}
        for pkg, pkg_branches in pkg_names.items():
            pkg_br = {el[0] for el in pkg_branches}
            inherited_branches = set()
            for inherited_branch in lut.branch_inheritance:
                if inherited_branch not in pkg_br:
                    inherited_branches.add(inherited_branch)
                    inherited_branches.update(lut.branch_inheritance[inherited_branch])
            if pkg not in pkgs_branches:
                pkgs_branches[pkg] = inherited_branches
            else:
                pkgs_branches[pkg].update(inherited_branches)
        return pkgs_branches

    def _get_last_packages_versions(self, pkg_names: Iterable[str]) -> None:
        """
        Get last package versions for active branches.
        """
        self.status = False
        tmp_table = make_tmp_table_name("pkg_names")

        response = self.send_sql_request(
            self.sql.get_packages_versions_for_show_branches.format(
                tmp_table=tmp_table
            ),
            external_tables=[
                {
                    "name": tmp_table,
                    "structure": [("pkg_name", "String")],
                    "data": [{"pkg_name": p} for p in pkg_names],
                }
            ],
        )
        if not self.sql_status:
            return None
        if not response:
            _ = self.store_error({"message": "No packages data found in DB"})
            return None

        self.packages_versions = {
            (el[1], el[-1]): PackageVersion(*el) for el in response
        }
        self.status = True

    def _get_done_tasks(
        self, pkgs_branches: dict[str, set[str]]
    ) -> Union[dict[str, list[Task]], None]:
        """
        Get `DONE` tasks by package names and branches.
        """
        self.status = False
        tmp_table = make_tmp_table_name("pkg_names")
        external_tables = [
            {
                "name": tmp_table,
                "structure": [
                    ("pkg_name", "String"),
                    ("pkgset_name", "String"),
                ],
                "data": [
                    {"pkg_name": name, "pkgset_name": br}
                    for name, branches in pkgs_branches.items()
                    for br in branches
                ],
            }
        ]
        response = self.send_sql_request(
            self.sql.get_done_tasks_by_packages_and_branches.format(
                tmp_table=tmp_table
            ),
            external_tables=external_tables,
        )
        if not self.sql_status:
            return None
        if not response:
            _ = self.store_error({"message": "No 'DONE' tasks found in DB"})
            return None

        # filter tasks by package name
        pkg_tasks: dict[str, list[Task]] = {}
        for task in (Task(*el) for el in response):
            if task.package not in pkg_tasks:
                pkg_tasks[task.package] = []
            pkg_tasks[task.package].append(task)
        self.status = True
        return pkg_tasks

    def _get_done_tasks_history(
        self, branches: tuple[str, ...]
    ) -> Union[dict[int, TaskHistory], None]:
        """
        Get a list of tasks history in the `DONE` status for each branch of the package.
        """

        self.status = False
        response = self.send_sql_request(
            self.sql.get_done_tasks_history.format(branches=branches)
        )
        if not self.sql_status:
            return None
        if not response:
            _ = self.store_error({"message": "No tasks history found in DB"})
            return None

        self.status = True
        return {t.id: t for t in (TaskHistory(*el) for el in response)}

    def _get_task_history(self, pkg_names: dict[str, list[tuple[str, int]]]):
        """
        Find `DONE` tasks by given package names and branch in accordance to
        task history and branch inheritance order.
        """

        self.status = False

        pkgs_branches = self._get_pkgs_branches(pkg_names)
        _all_branches = {br for branches in pkgs_branches.values() for br in branches}

        # get 'DONE' tasks by package names and branches
        pkg_tasks = self._get_done_tasks(pkgs_branches)
        if not self.status:
            return None

        # process tasks
        class PackageBranchPair(NamedTuple):
            name: str
            branch: str

        tasks: dict[PackageBranchPair, list[Task]] = {}
        for package, _tasks in pkg_tasks.items():
            # cut tasks list until the first task in given branch
            # we don't need them here due to errata history contents for
            # current branch is collected directly by packages names
            for br in pkgs_branches[package]:
                i = 0
                for ii, t in enumerate(_tasks):
                    if t.branch == br:
                        i = ii
                tasks[PackageBranchPair(package, br)] = _tasks[i:]

        if all(v == [] for v in tasks.values()):
            self.status = True
            return None

        tasks_history = self._get_done_tasks_history(tuple(_all_branches))
        if not self.status:
            return None

        # get the map of latest task of each branch
        newest_tasks: dict[str, TaskHistory] = {}
        for task in tasks_history.values():
            if (
                task.branch not in newest_tasks
                or task.changed > newest_tasks[task.branch].changed
            ):
                newest_tasks[task.branch] = task

        branch_history: dict[str, set[int]] = {}

        for branch, task in newest_tasks.items():
            t = task
            tasks_set = set()
            intermediate_branches = set()

            while True:
                tasks_set.add(t.id)

                if t.prev not in tasks_history:
                    # End of the list
                    break

                t = tasks_history[t.prev]

                if t.branch != branch and t.branch not in intermediate_branches:
                    intermediate_branches.add(t.branch)

            branch_history[branch] = tasks_set

        # filter out packages tasks using branch history
        for package, _tasks in tasks.items():
            if not _tasks:
                continue
            # build task history using branch inheritance order
            _all_pkg_task_branches = {t.branch for t in _tasks}
            for _branch in lut.branch_inheritance[package.branch]:
                # skip if there is no tasks found for branch
                if _branch not in _all_pkg_task_branches:
                    continue
                # found first matched branch form branch inheritance list
                filtered_tasks = [t for t in _tasks if t.id in branch_history[_branch]]
                index_to_cut = next(
                    (
                        i
                        for i, task in enumerate(filtered_tasks)
                        if (task.branch, task.id) in pkg_names[package.name]
                    ),
                    None,
                )
                if index_to_cut is None:
                    break
                for task in filtered_tasks[: index_to_cut + 1]:
                    if not task:
                        break
                    if package not in self.erratas_packages:
                        prev_package = self.erratas_packages.get(
                            (package.name, tasks[package][-1].branch)
                        )
                        if (
                            prev_package
                            and (package.name, package.branch) in self.packages_versions
                        ):
                            if compare_versions(
                                version1=self.packages_versions[
                                    (package.name, package.branch)
                                ].version,
                                release1=self.packages_versions[
                                    (package.name, package.branch)
                                ].release,
                                version2=prev_package.version,
                                release2=prev_package.release,
                            ) in (
                                VersionCompareResult.EQUAL,
                                VersionCompareResult.GREATER_THAN,
                            ):
                                self.erratas_packages[package] = PackageScheme(
                                    **asdict(prev_package)
                                )
                                self.erratas_packages[package].branch = package.branch
                            else:
                                break
                break
        self.status = True

    def _sort_erratas(self):
        """
        Sort the Erratas list by task state.
        """

        def _task_state_index(state: str) -> int:
            return {
                "DONE": 0,
                "EPERM": -1,
                "TESTED": -2,
            }.get(state, -100)

        self.erratas = sorted(
            self.erratas, key=lambda k: _task_state_index(k.task_state)
        )

    def get(self):
        vuln_id = self.args["vuln_id"]

        # Get list of errata by vuln ID to Errata references matching
        get_errata_by_cve_id(self, vuln_id)
        if not self.status:
            return self.error
        self._sort_erratas()

        self.erratas_packages = {
            (el.pkg_name, el.branch): PackageScheme(
                pkghash=el.pkg_hash,
                branch=el.branch,
                name=el.pkg_name,
                version=el.pkg_version,
                release=el.pkg_release,
                errata_id=el.id,
                task_id=el.task_id,
                subtask_id=el.subtask_id,
                task_state=el.task_state,
            )
            for br in sort_branches(lut.known_branches)
            for el in self.erratas
            if br == el.branch
        }

        package_names = self._get_package_names(self.erratas_packages)

        # Get last packages versions
        self._get_last_packages_versions(package_names.keys())
        if not self.status:
            return self.error

        self._get_task_history(package_names)
        for pkg, pkg_inf in self.packages_versions.items():
            if pkg in self.erratas_packages:
                self.erratas_packages[pkg].last_version = PackageMeta(
                    pkghash=pkg_inf.hash,
                    name=pkg_inf.name,
                    branch=pkg_inf.branch,
                    version=pkg_inf.version,
                    release=pkg_inf.release,
                )

        packages = [
            el.asdict()
            for _, el in self.erratas_packages.items()
            if el.last_version is not None
        ]

        res = {"request_args": self.args, "length": len(packages), "packages": packages}

        return res, 200
