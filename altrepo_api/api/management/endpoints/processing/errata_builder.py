# ALTRepo API
# Copyright (C) 2021-2024  BaseALT Ltd

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

from typing import Iterable

from altrepodb_libs import PackageCveMatch, VersionCompareResult

from altrepo_api.api.base import APIWorker

from .base import (
    ErrataBuilderError,
    CveCpmHashes,
    ErrataPoint,
    PackageTask,
    PackageVersion,
    cve_in_errata_references,
    collect_erratas,
    find_errata_by_package_task,
    get_closest_task,
    package_is_vulnerable,
    version_release_compare,
)
from .helpers import (
    get_pkgs_changelog,
    get_pkgs_done_tasks,
    get_pkgs_versions,
    get_build_tasks_by_pkg_nevr,
    get_cves_versions_matches,
    # get_related_erratas_by_cve_ids,
    get_related_erratas_by_pkgs_names,
)
from .sql import sql
from ..tools.base import Errata
from ..tools.changelog import vulns_from_package_changelog


class ErrataBuilder(APIWorker):
    """Handles Errata records modification."""

    def __init__(self, connection, branches: tuple[str, ...]):
        self.branches = branches
        self.conn = connection
        self.sql = sql
        super().__init__()

    def _get_possible_errata_points(
        self,
        pkgs_cve_matches: Iterable[PackageCveMatch],
        pkgs_versions: dict[int, PackageVersion],
    ) -> set[ErrataPoint]:
        # get packages history
        pkgs_tasks = get_pkgs_done_tasks(self, {m.pkg_name for m in pkgs_cve_matches})
        if not self.status:
            self.store_error({"message": "Failed to get packages tasks from DB"})
            raise ErrataBuilderError("Failed to get packages tasks from DB")

        # get CVE versions matches
        cve_cpm_versions = get_cves_versions_matches(
            self,
            {
                CveCpmHashes(m.vuln_hash, m.cpm_cpe_hash, m.cpm_version_hash)
                for m in pkgs_cve_matches
            },
        )
        if not self.status:
            raise ErrataBuilderError("Failed to get CVE versions matches from DB")

        errata_points = set()

        # loop through matches and find possible errata creation point
        all_tasks: dict[str, list[PackageTask]] = {}
        for t in (x for xx in pkgs_tasks.values() for x in xx):
            all_tasks.setdefault(t.branch, []).append(t)

        for match_ in (m for m in pkgs_cve_matches if not m.is_vulnerable):
            # check if any tasks found for package in a given branch
            if not all_tasks.get(pkgs_versions[match_.pkg_hash].branch):
                continue

            for cpm_ver in cve_cpm_versions.get(match_.vuln_hash, []):
                for tasks in all_tasks.values():
                    next_task = tasks[0]
                    # only one task found in history
                    if len(tasks) == 1:
                        errata_points.add(ErrataPoint(next_task, None, cpm_ver))
                        continue
                    # process task history
                    vulnerable_found = False
                    for t in tasks[1:]:
                        # skip tasks with package version is not vulnerable
                        if not package_is_vulnerable(t, cpm_ver.versions):
                            next_task = t
                            continue
                        # finally got vulnerable package version
                        errata_points.add(ErrataPoint(next_task, t, cpm_ver))
                        vulnerable_found = True
                        break
                    # use the oldest one task found in current branch as errata point
                    # candidate
                    if not vulnerable_found:
                        errata_points.add(ErrataPoint(tasks[-1], None, cpm_ver))

        return errata_points

    def build_erratas_on_cpe_add(
        self, pkgs_cve_matches: list[PackageCveMatch]
    ) -> tuple[list[ErrataPoint], list[tuple[Errata, str]]]:
        if not pkgs_cve_matches:
            self.logger.info("No packages' CVE matches found to be processed")
            return [], []

        # collect affected packages names and hashes
        pkgs_names = {m.pkg_name for m in pkgs_cve_matches}
        pkgs_hashes = {m.pkg_hash for m in pkgs_cve_matches}

        # get packages versions
        pkgs_versions = get_pkgs_versions(self, pkgs_hashes)
        print("DBG", pkgs_hashes)
        if not self.status:
            self.store_error({"message": "Failed to get packages versions from DB"})
            raise ErrataBuilderError("Failed to get packages versions from DB")

        # get existing erratas by packages names
        all_erratas = get_related_erratas_by_pkgs_names(
            self, packages=pkgs_names, exclude_discarded=True
        )
        if not self.status:
            self.store_error({"message": "Failed to get erratas by package' names"})
            raise ErrataBuilderError("Failed to get erratas by package' names")

        erratas_by_package: dict[str, list[Errata]] = {}

        # build existing errata mapping
        for errata in all_erratas.values():
            erratas_by_package.setdefault(errata.pkg_name, list()).append(errata)

        erratas_for_update: list[tuple[Errata, str]] = []
        erratas_for_create: list[ErrataPoint] = []

        # look for possible errata creation points
        possible_errata_points = self._get_possible_errata_points(
            pkgs_cve_matches, pkgs_versions
        )

        if not possible_errata_points:
            self.logger.debug(
                f"No possible errata creation points found for {pkgs_names}"
            )
            return [], []

        # get packages changelogs
        pkgs_changelogs = get_pkgs_changelog(
            self, {ep.task.hash for ep in possible_errata_points}
        )
        if not self.status:
            self.store_error({"message": "Failed to get packages changelogs from DB"})
            raise ErrataBuilderError("Failed to get packages changelogs from DB")

        # loop through possible errata points
        for ep in possible_errata_points:
            # collect existing erratas by package name and branch
            existing_erratas = collect_erratas(ep.task, erratas_by_package)
            exact_errata = find_errata_by_package_task(ep.task, existing_erratas)
            # got existing errata to be updated
            if exact_errata is not None:
                # CVE ID already in existintg errata for given package
                if cve_in_errata_references(ep.cvm.id, exact_errata):
                    continue
                # collect errata for update and continue
                self.logger.debug(
                    f"Found exact errata to be updated: {ep.cvm.id}: {exact_errata}"
                )
                erratas_for_update.append((exact_errata, ep.cvm.id))
                continue
            # check exiting erratas history for CVE was closed already
            closing_errata_found = False
            for errata in existing_erratas:
                if not cve_in_errata_references(ep.cvm.id, errata):
                    # skip errata that not contains given CVE
                    continue
                # 1. errata branch matches and package version-release is less or equal
                if version_release_compare(
                    v1=errata.pkg_version,
                    r1=errata.pkg_release,
                    v2=ep.task.version,
                    r2=ep.task.release,
                ) in (VersionCompareResult.EQUAL, VersionCompareResult.LESS_THAN):
                    if errata.pkgset_name == ep.task.branch:
                        # found errata that closes given CVE in current branch
                        closing_errata_found = True
                        self.logger.debug(
                            f"Found errata that closes {ep.cvm.id} in branch {ep.task.branch}: {errata}"
                        )
                        continue
                    else:
                        # found errata that closes given CVE in current branch inheritance list
                        closing_errata_found = True
                        self.logger.debug(
                            f"Found errata that closes {ep.cvm.id} for branch {ep.task.branch}: {errata}"
                        )
                        continue
            if closing_errata_found:
                continue
            # XXX: no erratas were found that closes given CVE
            # 1. check package changelog to clarify exact errata creation point
            ep_found = False
            pkg_changelog = pkgs_changelogs[ep.task.hash]

            for chlog, vulns in zip(
                pkg_changelog.changelog, vulns_from_package_changelog(pkg_changelog)
            ):
                # TODO: in fact there should be existing errata for CVEs that are closed by changelog
                if ep.cvm.id in vulns:
                    # found exact changelog record that closes given CVE
                    task = get_closest_task(
                        ep.task.branch,
                        get_build_tasks_by_pkg_nevr(self, ep.task.name, chlog.evr),
                    )
                    if task:
                        _ep = ErrataPoint(task=task, prev_task=None, cvm=ep.cvm)
                        erratas_for_create.append(_ep)
                        self.logger.debug(
                            f"Found most suitable errata point for {ep.cvm.id} in {ep.task.branch}: {_ep}"
                        )
                        ep_found = True
                        break
            if ep_found:
                continue
            # 2. XXX: nothing suitable was found
            self.logger.debug(
                f"No suitable errata creaton point was found for {ep.cvm.id} on {ep.task.name} in {ep.task.branch}"
            )

        return erratas_for_create, erratas_for_update
