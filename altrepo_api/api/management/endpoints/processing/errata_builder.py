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

from typing import Iterable, Optional
from uuid import UUID

from altrepodb_libs import PackageCveMatch

from altrepo_api.api.base import APIWorker
from altrepo_api.api.misc import lut
from altrepo_api.api.errata.endpoints.common import CVE_ID_PREFIX

from .base import (
    ErrataBuilderError,
    ErrataHandlerError,
    ChangelogErrataPoint,
    CveCpmHashes,
    ErrataPoint,
    PackageTask,
    PackageVersion,
    cve_in_errata_references,
    collect_erratas,
    dedup_pcms,
    find_errata_by_package_task,
    get_closest_task,
    package_is_vulnerable,
    version_release_less_or_equal,
)
from .errata_handler import ErrataHandler
from .helpers import (
    get_pkgs_changelog,
    get_pkgs_done_tasks,
    get_pkgs_versions,
    get_build_tasks_by_pkg_nevr,
    get_cves_versions_matches,
    get_related_erratas_by_pkgs_names,
    get_affected_errata_ids_by_transaction_id,
    delete_errata_history_records,
    delete_errata_change_history_records,
)
from .sql import sql
from ..tools.base import ChangeReason, Errata
from ..tools.changelog import (
    PackageChangelog,
    split_evr,
    vulns_from_changelog,
    all_vulns_from_changelog,
)
from ..tools.errata_id import ErrataManageError, get_errataid_service, discard_errata_id


class ErrataBuilder(APIWorker):
    """Handles Errata records modification."""

    def __init__(
        self,
        connection,
        branches: tuple[str, ...],
        reason: ChangeReason,
        transaction_id: UUID,
        dry_run: bool,
    ):
        self.branches = branches
        self.conn = connection
        self.sql = sql
        self.transaction_id = transaction_id
        self.dry_run = dry_run
        self.eh = ErrataHandler(self.conn, reason, transaction_id, dry_run)
        self.rollback_errors = []
        super().__init__()

    @property
    def errata_records(self):
        return self.eh.errata_records

    @property
    def errata_change_records(self):
        return self.eh.errata_change_records

    def _get_packages_versions(self, pkgs_hashes: Iterable[int]):
        """Get packages' versions info by hashes."""

        pkgs_versions = get_pkgs_versions(self, pkgs_hashes)
        if not self.status:
            self.store_error({"message": "Failed to get packages versions from DB"})
            raise ErrataBuilderError("Failed to get packages versions from DB")
        return pkgs_versions

    def _get_pkgs_changelogs(self, pkgs_hashes: Iterable[int]):
        """Get packages changelogs by hashes."""

        pkgs_changelogs = get_pkgs_changelog(self, pkgs_hashes)
        if not self.status:
            self.store_error({"message": "Failed to get packages changelogs from DB"})
            raise ErrataBuilderError("Failed to get packages changelogs from DB")
        return pkgs_changelogs

    def _get_done_tasks(self, pkgs_names: Iterable[str]):
        """Get `DONE` tasks by packages' names."""

        pkgs_tasks = get_pkgs_done_tasks(self, pkgs_names)
        if not self.status:
            self.store_error({"message": "Failed to get packages tasks from DB"})
            raise ErrataBuilderError("Failed to get packages tasks from DB")
        return pkgs_tasks

    def _get_cve_matchings(self, cpm_hashes: Iterable[CveCpmHashes]):
        """Get CVE' CPE matches using (vuln_hahs, cpe_hash, cpe_version_hash) triplets."""

        cve_cpm_versions = get_cves_versions_matches(self, cpm_hashes)
        if not self.status:
            self.store_error({"message": "Failed to get CVE versions matches from DB"})
            raise ErrataBuilderError("Failed to get CVE versions matches from DB")
        return cve_cpm_versions

    def _get_existing_erratas(self, pkgs_names: Iterable[str]):
        """Get existing erratas by packages' names excluding discarded ones."""

        erratas_by_package: dict[str, list[Errata]] = {}

        # get existing erratas by packages names
        all_erratas = get_related_erratas_by_pkgs_names(
            self, packages=pkgs_names, exclude_discarded=True
        )
        if not self.status:
            self.store_error({"message": "Failed to get erratas by package' names"})
            raise ErrataBuilderError("Failed to get erratas by package' names")

        # build existing Errata mapping by packages' names
        for errata in all_erratas.values():
            erratas_by_package.setdefault(errata.pkg_name, list()).append(errata)

        return erratas_by_package

    def _get_possible_errata_points(
        self,
        pkgs_cve_matches: Iterable[PackageCveMatch],
        pkgs_versions: dict[int, list[PackageVersion]],
    ):
        """Collect possible Errata creation points usin given packages' CVE matches.
        Collected set of ErrataPoint objects could have 'prev_task' field to 'None' -
        that indicates there is no previous task with vulnerable package version found.
        """

        errata_points: set[tuple[ErrataPoint, int]] = set()

        pkgs_names = {m.pkg_name for m in pkgs_cve_matches}
        cpm_hashes = {
            CveCpmHashes(m.vuln_hash, m.cpm_cpe_hash, m.cpm_version_hash)
            for m in pkgs_cve_matches
        }

        # get packages' tasks history
        pkgs_tasks = self._get_done_tasks(pkgs_names)
        # group packages' tasks by branch
        tasks_by_branch: dict[str, list[PackageTask]] = {}
        for t in (x for xx in pkgs_tasks.values() for x in xx):
            tasks_by_branch.setdefault(t.branch, []).append(t)
        # get CVE versions matches
        cve_cpm_versions = self._get_cve_matchings(cpm_hashes)

        # loop through matches and find possible errata creation point
        for idx, m in enumerate(pkgs_cve_matches):
            # skip matches that marked as vulnerable from possible Errata creation points
            if m.is_vulnerable:
                continue

            branches = [v.branch for v in pkgs_versions[m.pkg_hash]]
            # check if any tasks found for package in a given branch
            for branch in branches:
                branch_tasks = tasks_by_branch.get(branch, [])

                # skip if not tasks found for current branch
                if not branch_tasks:
                    continue

                # loop through CVE' matches and search for suitable package' task
                for cpm_ver in cve_cpm_versions.get(m.vuln_hash, []):
                    # skip CVE' CPE matches by version hashes
                    if cpm_ver.hashes.cpm_version_hash != m.cpm_version_hash:
                        continue

                    next_task = branch_tasks[0]

                    # only one task found in history
                    if len(branch_tasks) == 1:
                        if not package_is_vulnerable(next_task, cpm_ver.versions):
                            # got only one task in current branch and it has not
                            # vulnerable package' version -> set 'prev_task' to 'None'
                            errata_points.add(
                                (ErrataPoint(next_task, None, cpm_ver), idx)
                            )
                        continue

                    # look for a pair of tasks which closes vulnerability by version update
                    vulnerable_found = False
                    for task in branch_tasks[1:]:
                        # skip tasks with package version is not vulnerable
                        if not package_is_vulnerable(task, cpm_ver.versions):
                            next_task = task
                            continue
                        # finally got task with vulnerable package' version -> good point
                        # to create an Errata
                        errata_points.add((ErrataPoint(next_task, task, cpm_ver), idx))
                        vulnerable_found = True
                        break
                    # got no task in current branch that has vulnerable package' version
                    # -> use the last one and set 'prev_task' to 'None'
                    if not vulnerable_found:
                        errata_points.add(
                            (ErrataPoint(branch_tasks[-1], None, cpm_ver), idx)
                        )

        return errata_points

    def _get_exact_erratas_for_update(
        self,
        erratas_by_package: dict[str, list[Errata]],
        errata_points: Iterable[tuple[ErrataPoint, int]],
    ):
        """Collect existing Erratas for update that matches to given Errata creation
        points and doesn't contain given CVEs.
        """

        erratas_for_update: list[tuple[Errata, ErrataPoint, int]] = []

        for ep, idx in errata_points:
            # filter existing erratas by exact task
            exact_errata = find_errata_by_package_task(
                ep.task, erratas_by_package.get(ep.task.name, [])
            )
            # got existing errata to be updated
            if exact_errata is not None:
                # CVE ID already in existintg errata for given package
                if cve_in_errata_references(ep.cvm.id, exact_errata):
                    continue
                # collect errata for update and continue
                erratas_for_update.append((exact_errata, ep, idx))

        return erratas_for_update

    def _get_closing_erratas(
        self,
        pkgs_cve_matches: Iterable[PackageCveMatch],
        erratas_by_package: dict[str, list[Errata]],
        pkgs_versions: dict[int, list[PackageVersion]],
    ):
        """Collect Erratas that closes vulnerabilities from packages CVE matches."""

        closing_erratas: dict[int, dict[str, Errata]] = {}

        for idx, m in enumerate(pkgs_cve_matches):
            for p in pkgs_versions[m.pkg_hash]:
                erratas = collect_erratas(
                    p.branch, erratas_by_package.get(m.pkg_name, [])
                )
                for errata in erratas:
                    # FIXME: skip branches without tasks history
                    if p.branch in lut.taskless_branches:
                        continue
                    # skip erratas that not contains given CVE
                    if not cve_in_errata_references(m.vuln_id, errata):
                        continue
                    # check errata' package version and release
                    if version_release_less_or_equal(errata, p):
                        if errata.pkgset_name == p.branch:
                            # found errata that closes given CVE in current branch
                            self.logger.debug(
                                f"Found errata that closes {m.vuln_id} in branch {p.branch}: {errata.id}"
                            )
                        else:
                            # found errata that closes given CVE in current branch inheritance list
                            self.logger.debug(
                                f"Found errata that closes {m.vuln_id} for branch {p.branch} from {errata.pkgset_name}: {errata.id}"
                            )
                        closing_erratas.setdefault(idx, dict())[p.branch] = errata
                        break

        return closing_erratas

    def _build_erratas_from_changelogs(
        self,
        pkgs_versions: dict[int, list[PackageVersion]],
        pkgs_changelogs: dict[int, PackageChangelog],
        erratas_by_package: dict[str, list[Errata]],
    ) -> None:
        """Proceed with packages changelog to create new or update existing erratas
        for CVEs mentioned in changelog.
        """

        pkgs_vulns_from_chlog: dict[int, list[set[str]]] = {}
        for h, chlog in pkgs_changelogs.items():
            pkgs_vulns_from_chlog[h] = vulns_from_changelog(chlog)

        def find_errata_by_package_chlog(
            branch: str, name: str, evr: str, erratas: list[Errata]
        ) -> Optional[Errata]:
            """Find exact Errata from list matching by by branch, package name,
            version and release.
            """

            _, version, release = split_evr(evr)

            for e in erratas:
                if (e.pkgset_name, e.pkg_name, e.pkg_version, e.pkg_release) == (
                    branch,
                    name,
                    version,
                    release,
                ):
                    return e
            return None

        def cves_from_vulns(vulns: set[str]) -> set[str]:
            return {v for v in vulns if v.startswith("CVE-")}

        def errata_cves_diff(cves: Iterable[str], errata: Errata) -> Optional[set[str]]:
            res = set()
            refs = {e.link for e in errata.references}
            for cve in cves:
                if cve not in refs:
                    res.add(cve)
            return res if res else None

        def make_errata_creation_point(
            branch: str, name: str, evr: str, cve_ids: Iterable[str]
        ) -> Optional[ChangelogErrataPoint]:
            build_tasks = get_build_tasks_by_pkg_nevr(self, name, evr)
            task = get_closest_task(branch, build_tasks)
            if task is None:
                return None
            return ChangelogErrataPoint(task=task, evr=evr, cve_ids=tuple(cve_ids))

        def make_errata_update_point(
            errata: Errata, cve_ids: Iterable[str], evr: str
        ) -> tuple[Errata, ChangelogErrataPoint]:
            return errata, ChangelogErrataPoint(
                task=PackageTask(
                    task_id=errata.task_id,
                    subtask_id=errata.subtask_id,
                    branch=errata.pkgset_name,
                    hash=errata.pkg_hash,
                    name=errata.pkg_name,
                    version=errata.pkg_version,
                    release=errata.pkg_release,
                    changed=errata.created,
                ),
                evr=evr,
                cve_ids=tuple(cve_ids),
            )

        #  a set of tuples of [branch, name, evr, cve_ids]
        uniq_bnevrv: set[tuple[str, str, str, tuple[str, ...]]] = set()
        uniq_chlog_create: set[ChangelogErrataPoint] = set()
        uniq_chlog_update: set[tuple[Errata, ChangelogErrataPoint]] = set()

        for h, chlog in pkgs_changelogs.items():
            pkg_versions = pkgs_versions[h]
            pkg_name = pkg_versions[0].name
            pkg_branches = [v.branch for v in pkg_versions]
            existing_erratas = erratas_by_package[pkg_name]
            # check if errata exists and not contains mentioned vulns
            for r, v in (
                (r, v) for r, v in zip(chlog.changelog, pkgs_vulns_from_chlog[h]) if v
            ):
                # XXX: collect only CVE IDs from changlog
                cves_from_chlog = tuple(cves_from_vulns(v))
                if not cves_from_chlog:
                    continue

                for branch in pkg_branches:
                    # FIXME: skip taskless branches
                    if branch in lut.taskless_branches:
                        continue
                    # check if current chlog record is already processed
                    if (branch, pkg_name, r.evr, cves_from_chlog) in uniq_bnevrv:
                        continue
                    uniq_bnevrv.add((branch, pkg_name, r.evr, cves_from_chlog))
                    # check if errata exists already
                    errata = find_errata_by_package_chlog(
                        branch, pkg_name, r.evr, existing_erratas
                    )
                    if errata is None:
                        # create new errata point
                        ep = make_errata_creation_point(
                            branch, pkg_name, r.evr, cves_from_chlog
                        )
                        if ep is None:
                            self.logger.warning(
                                f"Failed to create errata for in {branch} on {r}"
                            )
                            continue
                        # check if created errata point has existing errata
                        # filter existing erratas by exact task
                        exact_errata = find_errata_by_package_task(
                            ep.task, existing_erratas
                        )
                        # got existing errata to be updated
                        if exact_errata is not None:
                            # check if CVEs from changelog in errata
                            cves_diff = errata_cves_diff(cves_from_chlog, exact_errata)
                            if cves_diff is None:
                                continue
                            # update existing errata
                            e_, ep_ = make_errata_update_point(
                                exact_errata, cves_diff, r.evr
                            )
                            if (e_, ep_) not in uniq_chlog_update:
                                uniq_chlog_update.add((e_, ep_))
                                self.eh.add_errata_update_from_chlog(e_, ep_)
                            continue
                        if ep not in uniq_chlog_create:
                            uniq_chlog_create.add(ep)
                            self.eh.add_errata_create_from_chlog(ep)
                        continue
                    # check if CVEs from changelog in errata
                    cves_diff = errata_cves_diff(cves_from_chlog, errata)
                    if cves_diff is None:
                        continue
                    # update existing errata
                    e_, ep_ = make_errata_update_point(errata, cves_diff, r.evr)
                    if (e_, ep_) not in uniq_chlog_update:
                        uniq_chlog_update.add((e_, ep_))
                        self.eh.add_errata_update_from_chlog(e_, ep_)

    def build_erratas_on_cpe_add(self, pkgs_cve_matches: list[PackageCveMatch]) -> None:
        if not pkgs_cve_matches:
            self.logger.info("No packages' CVE matches found to be processed")
            return None

        # deduplicate packages' cve matches
        pkgs_cve_matches = dedup_pcms(pkgs_cve_matches)

        # collect affected packages names and hashes
        pkgs_names = {m.pkg_name for m in pkgs_cve_matches}
        pkgs_hashes = {m.pkg_hash for m in pkgs_cve_matches}

        # get packages' versions and changelogs
        pkgs_versions = self._get_packages_versions(pkgs_hashes)
        pkgs_changelogs = self._get_pkgs_changelogs(pkgs_hashes)

        # check if any package has changelog record that closes CVE from matches
        def any_package_has_match_cves_in_chlog() -> bool:
            # check if any packages has CVEs mentioned in changelog
            for chlog in pkgs_changelogs.values():
                # TODO: handle other vulnerabilities types other than CVE
                # if all_vulns_from_changelog(chlog):
                if any(
                    v.startswith(CVE_ID_PREFIX) for v in all_vulns_from_changelog(chlog)
                ):
                    return True
            return False

        any_pkg_has_cve_in_chlog = any_package_has_match_cves_in_chlog()

        # get possible errata creation points
        possible_errata_points = self._get_possible_errata_points(
            pkgs_cve_matches, pkgs_versions
        )

        # collect existing Erratas by packages' names
        erratas_by_package = self._get_existing_erratas(pkgs_names)

        if not possible_errata_points and not any_pkg_has_cve_in_chlog:
            self.logger.debug(
                f"No possible Errata creation points found for {pkgs_names}"
            )
            return None

        if any_pkg_has_cve_in_chlog:
            # check packages' changelogs for possible errata create or update
            self._build_erratas_from_changelogs(
                pkgs_versions, pkgs_changelogs, erratas_by_package
            )

        # nothing left to do
        if not possible_errata_points:
            return None

        # collect exact existing Erratas for possible Errata points
        exact_erratas_for_update = self._get_exact_erratas_for_update(
            erratas_by_package, possible_errata_points
        )

        # handle found existing Erratas to be updated
        for errata, ep, idx in exact_erratas_for_update:
            self.logger.debug(f"Found exact errata to be updated: {ep}: {errata}")
            self.eh.add_errata_update_from_ep(errata, ep, pkgs_cve_matches[idx])
            # remove errata point from set as processed
            possible_errata_points.discard((ep, idx))

        # iterate through a copy of 'possible_errata_points'
        for ep, idx in list(possible_errata_points):
            # drop errata points that has no previous task
            if ep.prev_task is None:
                possible_errata_points.discard((ep, idx))
                continue

            # filter existing erratas by exact task
            exact_errata = find_errata_by_package_task(
                ep.task, erratas_by_package.get(ep.task.name, [])
            )
            # got existing errata for errata point
            if exact_errata is not None:
                # CVE ID already in existintg errata for given package -> skip it
                if cve_in_errata_references(ep.cvm.id, exact_errata):
                    continue
                else:
                    # update existing errata
                    self.eh.add_errata_update_from_ep(
                        exact_errata, ep, pkgs_cve_matches[idx]
                    )
                    continue
            # no existing errata was found -> create new one
            self.eh.add_errata_create_from_ep(ep, pkgs_cve_matches[idx])

    def commit(self) -> None:
        try:
            self.eh.commit()
        except ErrataHandlerError as e:
            self.error = self.eh.error
            raise ErrataBuilderError("Failed while handling Errata updates") from e

    def rollback(self) -> bool:
        # delete all `ErrataChangeHistory` and related `ErrataHistory` records
        # using transaction ID and Errata IDs
        if self.dry_run:
            self.logger.warning("DRY_RUN: Errata manage transaction rollback")
            return True
        self.logger.warning("Errata manage transaction rollback")

        # collect affected Errata IDS
        errata_ids = get_affected_errata_ids_by_transaction_id(
            self, str(self.transaction_id)
        )
        if not self.status:
            self.rollback_errors.append(self.error)

        # delete ErrataChangeHistory records
        delete_errata_change_history_records(self, str(self.transaction_id))
        if not self.status:
            self.rollback_errors.append(self.error)

        # delete ErrataHistory records
        delete_errata_history_records(self, errata_ids)
        if not self.status:
            self.rollback_errors.append(self.error)

        # discard registered Errata IDs
        error = discard_errata_ids(self.dry_run, errata_ids)
        if error:
            self.store_error(
                {"message": f"Transaction rollback failed: {error}"},
                severity=self.LL.CRITICAL,
                http_code=500,
            )
            self.rollback_errors.append(self.error)

        return self.status


def discard_errata_ids(dry_run, errata_ids: Iterable[str]) -> Optional[str]:
    errors = []
    ids = list(errata_ids)

    try:
        eid_service = get_errataid_service(dry_run)
    except ErrataManageError:
        return "Failed to connect to ErrataID service"

    for idx, errata_id in enumerate(ids):
        try:
            discard_errata_id(eid_service, errata_id)
        except ErrataManageError:
            # XXX: ignore ErrataID service errors here
            errors.append(f"Failed to discard Errata ID '{errata_id}'")
            for i in range(idx, len(ids)):
                errors.append(f"Errata ID '{ids[i]}' was not discarded")

    if errors:
        return "; ".join(errors)

    return None
