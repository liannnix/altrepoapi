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

from itertools import pairwise
from typing import Iterable, Optional
from uuid import UUID

from altrepodb_libs import PackageCveMatch

from altrepo_api.api.base import APIWorker
from altrepo_api.api.errata.endpoints.common import CVE_ID_PREFIX

from .base import (
    ErrataBuilderError,
    ErrataHandlerError,
    ChangelogErrataPoint,
    CveVersionsMatch,
    CveCpmHashes,
    ErrataPoint,
    PackageTask,
    PackageVersion,
    is_cve_in_errata_references,
    cves_from_vulns,
    errata_cves_diff,
    dedup_pcms,
    find_errata_by_package_task,
    group_tasks_by_branch,
    group_tasks_by_branch_and_name,
    is_package_vulnerable,
    is_cpm_version_upper_boung_gt,
    is_version_release_eq,
)
from .errata_handler import ErrataHandler
from .helpers import (
    get_pkgs_changelog,
    get_pkgs_done_tasks,
    get_pkgs_versions,
    get_cves_versions_matches,
    get_related_erratas_by_pkgs_names,
    get_affected_errata_ids_by_transaction_id,
    delete_errata_history_records,
    delete_errata_change_history_records,
)
from .sql import sql
from ..tools.base import ChangeReason, Errata, PncRecordType
from ..tools.changelog import (
    ChangelogRecord,
    PackageChangelog,
    split_evr,
    vulns_from_changelog,
    all_vulns_from_changelog,
    vulns_from_changelog_record,
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
        type: PncRecordType,
    ):
        self.branches = branches
        self.conn = connection
        self.sql = sql
        self.transaction_id = transaction_id
        self.dry_run = dry_run
        self._type = type
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
        pkgs_tasks: dict[str, list[PackageTask]],
    ) -> set[tuple[ErrataPoint, int]]:
        """Collect possible Errata creation points using given packages' CVE matches."""

        errata_points: set[tuple[ErrataPoint, int]] = set()

        if not pkgs_tasks:
            self.logger.info("No build tasks found in DB to be processed for Errata")
            return errata_points

        cpm_hashes = {
            CveCpmHashes(m.vuln_hash, m.cpm_cpe_hash, m.cpm_version_hash)
            for m in pkgs_cve_matches
        }

        tasks_by_branch = group_tasks_by_branch(pkgs_tasks)
        tasks_by_branch_and_package = group_tasks_by_branch_and_name(pkgs_tasks)
        # get CVE versions matches
        cve_cpm_versions = self._get_cve_matchings(cpm_hashes)

        # contains CVE match version range with highest upper bound
        # for a given branch, package and CVE
        pkg_cve_match_max_versions: dict[
            tuple[str, str, str], tuple[int, CveVersionsMatch]
        ] = {}

        # TODO: use existing exclusion rules from DB
        def skip_by_exclusion_rules(pcm: PackageCveMatch) -> bool:
            """Filter out PCM that excluded by existing rules."""
            return False

        def skip_cpm_version_by_upper_bound(cvm: CveVersionsMatch) -> bool:
            """Filter out version ranges with open upper bound."""
            return cvm.versions.version_end == ""

        # loop through matches and find suitable matches to be processed for errata points
        for idx, m in enumerate(pkgs_cve_matches):
            # skip matches that marked as vulnerable from possible Errata creation points
            # skip matches closed by exclusion rules set
            if m.is_vulnerable or skip_by_exclusion_rules(m):
                continue

            branches = [v.branch for v in pkgs_versions[m.pkg_hash]]
            # check if any tasks found for package in a given branch
            for branch in branches:
                # skip if no tasks found for current branch
                if not tasks_by_branch.get(branch, []):
                    continue

                # loop through CVE' matches and search for highest version range upper bound
                for cvm in (
                    c
                    for c in cve_cpm_versions.get(m.vuln_hash, [])
                    if (
                        # skip CVE' CPE matches by version hashes check
                        c.hashes.cpm_version_hash == m.cpm_version_hash
                        # skip CVE' CPE matches by version range bounds check
                        and not skip_cpm_version_by_upper_bound(c)
                    )
                ):
                    key_t = (branch, m.pkg_name, cvm.id)
                    if key_t not in pkg_cve_match_max_versions:
                        pkg_cve_match_max_versions[key_t] = (idx, cvm)
                        continue

                    _, prev_cvm = pkg_cve_match_max_versions[key_t]
                    if is_cpm_version_upper_boung_gt(cvm.versions, prev_cvm.versions):
                        pkg_cve_match_max_versions[key_t] = (idx, cvm)

        # use found suitable matches to build proper errata creation points
        for (branch, package, cve), (idx, cvm) in pkg_cve_match_max_versions.items():
            # collect build tasks for a specific package in a given branch
            pkg_tasks = tasks_by_branch_and_package.get(branch, {}).get(package, [])

            if not pkg_tasks:
                self.logger.debug(f"No build tasks found for {package} in {branch}")
                continue

            next_task = pkg_tasks[0]

            # only one task found in history
            if len(pkg_tasks) == 1:
                self.logger.info(
                    f"No suitable task found to create errata for {cve} on {package} in {branch}"
                )
                continue

            # look for a pair of tasks which closes vulnerability by version update
            vulnerable_found = False
            for task in pkg_tasks[1:]:
                # skip tasks with package version is not vulnerable
                if not is_package_vulnerable(task, cvm.versions):
                    next_task = task
                    continue
                # finally got task with vulnerable package' version -> good point
                # to create an Errata
                errata_points.add((ErrataPoint(next_task, task, cvm), idx))
                vulnerable_found = True
                break
            # got no task in current branch that has vulnerable package' version
            if not vulnerable_found:
                self.logger.info(
                    f"No task for package {package} found for {cve} in {branch} as vulnerable"
                )

        return errata_points

    def _build_erratas_from_changelogs(
        self,
        pkgs_tasks: dict[str, list[PackageTask]],
        pkgs_versions: dict[int, list[PackageVersion]],
        pkgs_changelogs: dict[int, PackageChangelog],
        erratas_by_package: dict[str, list[Errata]],
    ) -> tuple[list[ChangelogErrataPoint], list[tuple[Errata, ChangelogErrataPoint]]]:
        create_errata_eps: list[ChangelogErrataPoint] = []
        update_errata_eps: list[tuple[Errata, ChangelogErrataPoint]] = []

        def get_errata_by_task(
            erratas: Iterable[Errata], task_id: int
        ) -> Optional[Errata]:
            for errata in erratas:
                if errata.task_id == task_id:
                    return errata
                return None

        def build_chlog_slice(
            tasks: list[PackageTask], chlog_zip: list[tuple[ChangelogRecord, set[str]]]
        ) -> list[tuple[PackageTask, set[str], str]]:
            chlog_slice: list[tuple[PackageTask, set[str], str]] = []

            # iterate through builsd tasks pairwise and collect CVEs from changelog if any
            last_idx = 0
            for task, prev_task in pairwise(tasks):
                all_cves = set()
                for idx, (rec, cves) in enumerate(chlog_zip):
                    # continue from last point
                    if idx < last_idx:
                        continue
                    _, version, release = split_evr(rec.evr)
                    all_cves.update(cves)
                    # got previous task EVR in a changelog
                    if is_version_release_eq(
                        v1=version,
                        r1=release,
                        v2=prev_task.version,
                        r2=prev_task.release,
                    ):
                        last_idx = idx
                        if all_cves:
                            chlog_slice.append((task, all_cves, rec.evr))
                        break
            # process the very first task in a branch history
            rec, cves = chlog_zip[last_idx]
            if cves:
                chlog_slice.append((tasks[-1], cves, rec.evr))

            return chlog_slice

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

        # group build tasks
        # tasks_by_branch = group_tasks_by_branch(pkgs_tasks)
        tasks_by_branch_and_package = group_tasks_by_branch_and_name(pkgs_tasks)

        pkgs_cves_from_chlog: dict[int, list[set[str]]] = {}
        for h, chlog in pkgs_changelogs.items():
            pkgs_cves_from_chlog[h] = [
                cves_from_vulns(v) for v in vulns_from_changelog(chlog)
            ]

        # loop through changelogs and check if there exists any errata create or update point
        for h, chlog in pkgs_changelogs.items():
            # short path if there is no changelog records that closes CVE at all
            if not any(cves for cves in pkgs_cves_from_chlog[h]):
                continue

            pkg_versions = pkgs_versions[h]
            pkg_name = pkg_versions[0].name

            # short path if there is no build tasks for a given package
            if pkg_name not in pkgs_tasks:
                continue

            # use only branches that has any build tasks in DB
            branches = [v.branch for v in pkg_versions if v.branch in pkgs_tasks]
            existing_erratas = erratas_by_package.get(pkg_name, [])

            for branch in branches:
                tasks = tasks_by_branch_and_package.get(branch, {}).get(pkg_name, [])

                # got no build tasks for a given branch -> nothing to do
                if not tasks:
                    continue

                if len(tasks) == 1:
                    self.logger.debug(
                        f"Got only one build task for {pkg_name} in {branch}"
                    )
                    task = tasks[0]
                    cves = pkgs_cves_from_chlog[h][0]
                    if cves:
                        self.logger.debug(f"task: {task.task_id}, cves: {cves}")
                        chlog_slice = [(task, cves, chlog.changelog[0].evr)]
                    else:
                        self.logger.debug(
                            f"No CVE found in changelog for {pkg_name} in {branch}"
                        )
                        continue
                else:
                    chlog_slice = build_chlog_slice(
                        tasks, list(zip(chlog.changelog, pkgs_cves_from_chlog[h]))
                    )

                # no CVEs from changelog where collected and mapped to build tasks
                if not chlog_slice:
                    self.logger.debug(
                        f"No CVE found in changelog for {pkg_name} in {branch}"
                    )
                    continue

                # collect existing erratas for using task IDs and package name
                # using task IDs ensures proper branch filtering
                erratas = [
                    e
                    for e in existing_erratas
                    if e.pkg_name == pkg_name
                    and e.task_id in {t.task_id for (t, *_) in chlog_slice}
                ]

                # do something with found tasks, CVEs and erratas
                for task, cves, evr in chlog_slice:
                    errata = get_errata_by_task(erratas, task.task_id)
                    if errata is None:
                        # add errata create point
                        create_errata_eps.append(
                            ChangelogErrataPoint(
                                task=task, evr=evr, cve_ids=tuple(cves)
                            )
                        )
                    else:
                        # check if existing errata should be updated
                        if errata_cves_diff(cves, errata) is None:
                            continue
                        update_errata_eps.append(
                            (
                                errata,
                                ChangelogErrataPoint(
                                    task=task, evr=evr, cve_ids=tuple(cves)
                                ),
                            )
                        )

        return create_errata_eps, update_errata_eps

    def build_erratas_on_add(
        self, pkgs_cve_matches: list[PackageCveMatch], pkg_name: Optional[str]
    ) -> None:
        if not pkgs_cve_matches:
            self.logger.info("No packages' CVE matches found to be processed")
            return None

        # deduplicate packages' cve matches
        pkgs_cve_matches = dedup_pcms(pkgs_cve_matches)

        # collect affected packages names and hashes
        if pkg_name is None:
            pkgs_names = {m.pkg_name for m in pkgs_cve_matches}
            pkgs_hashes = {m.pkg_hash for m in pkgs_cve_matches}
        else:
            pkgs_names = {
                m.pkg_name for m in pkgs_cve_matches if m.pkg_name == pkg_name
            }
            pkgs_hashes = {
                m.pkg_hash for m in pkgs_cve_matches if m.pkg_name == pkg_name
            }

        # get packages' versions and changelogs
        pkgs_tasks = self._get_done_tasks(pkgs_names)
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

        def is_already_closed_by_existing_errata(
            branch: str, cve: str, erratas: list[Errata]
        ) -> bool:
            if not erratas:
                return False

            for errata in (e for e in erratas if e.pkgset_name == branch):
                if is_cve_in_errata_references(cve, errata):
                    return True

            return False

        any_pkg_has_cve_in_chlog = any_package_has_match_cves_in_chlog()

        # get possible errata creation points
        possible_errata_points = self._get_possible_errata_points(
            pkgs_cve_matches, pkgs_versions, pkgs_tasks
        )

        if not possible_errata_points and not any_pkg_has_cve_in_chlog:
            self.logger.debug(
                f"No possible Errata creation points found for {pkgs_names}"
            )
            return None

        # collect existing Erratas by packages' names
        erratas_by_package = self._get_existing_erratas(pkgs_names)

        if any_pkg_has_cve_in_chlog:
            # check packages' changelogs for possible errata create or update
            erratas_to_create, erratas_to_update = self._build_erratas_from_changelogs(
                pkgs_tasks, pkgs_versions, pkgs_changelogs, erratas_by_package
            )
            for ep in erratas_to_create:
                self.eh.add_errata_create_from_chlog(ep)
            for errata, ep in erratas_to_update:
                self.eh.add_errata_update_from_chlog(errata, ep)

        # nothing left to do
        if not possible_errata_points:
            return None

        # iterate through a copy of 'possible_errata_points'
        for ep, idx in list(possible_errata_points):
            # drop errata points that has no previous task
            if ep.prev_task is None:
                continue

            pcm = pkgs_cve_matches[idx]
            existing_erratas = erratas_by_package.get(ep.task.name, [])

            # check if exist Errata that closes particular CVE in a given branch
            if is_already_closed_by_existing_errata(
                ep.task.branch, ep.cvm.id, existing_erratas
            ):
                continue

            # check if package' changelog closes a given CVE
            # XXX: ensure that all CVE closing records from changelog processed properly
            if any_pkg_has_cve_in_chlog and ep.cvm.id in all_vulns_from_changelog(
                pkgs_changelogs[pcm.pkg_hash]
            ):
                continue

            # filter existing erratas by exact task
            exact_errata = find_errata_by_package_task(ep.task, existing_erratas)
            # got existing errata for errata point
            if exact_errata is not None:
                # CVE ID already in existintg errata for given package -> skip it
                if is_cve_in_errata_references(ep.cvm.id, exact_errata):
                    continue
                else:
                    # update existing errata
                    self.logger.debug(
                        f"Found exact errata to be updated: {ep}: {exact_errata}"
                    )
                    self.eh.add_errata_update_from_ep(exact_errata, ep, pcm)
                    continue
            # no existing errata was found -> create new one
            self.eh.add_errata_create_from_ep(ep, pcm)

    def build_erratas_on_delete(
        self, pkgs_cve_matches: list[PackageCveMatch], pkg_name: Optional[str]
    ) -> None:
        if not pkgs_cve_matches:
            self.logger.info("No packages' CVE matches found to be processed")
            return None

        # collect affected packages names and hashes
        if pkg_name is None:
            pkgs_names = {m.pkg_name for m in pkgs_cve_matches}
            pkgs_hashes = {m.pkg_hash for m in pkgs_cve_matches}
        else:
            pkgs_names = {
                m.pkg_name for m in pkgs_cve_matches if m.pkg_name == pkg_name
            }
            pkgs_hashes = {
                m.pkg_hash for m in pkgs_cve_matches if m.pkg_name == pkg_name
            }

        # no packages matches left for specific package name
        if not pkgs_names:
            return None

        # collect all CVE IDs from matches
        pcms_cve_ids = {m.vuln_id for m in pkgs_cve_matches}

        # get packages' changelogs
        pkgs_changelogs = self._get_pkgs_changelogs(pkgs_hashes)

        # collect existing Erratas by packages' names, excluding those are has
        # no intersection by CVE IDs from packages' CVE matches
        def any_cve_ids_in_errata_references(cve_ids: set[str], e: Errata) -> bool:
            if cve_ids.intersection({r.link for r in e.references}):
                return True
            return False

        erratas_by_package: dict[str, list[Errata]] = {}
        for pkg, erratas in self._get_existing_erratas(pkgs_names).items():
            for errata in erratas:
                if any_cve_ids_in_errata_references(pcms_cve_ids, errata):
                    erratas_by_package.setdefault(pkg, []).append(errata)

        # no erratas found by packages' names
        if not erratas_by_package:
            return None

        cves_by_errata_ids: dict[str, set[str]] = {}
        erratas_by_cve: dict[str, list[tuple[Errata, str]]] = {}
        processed_cve_to_errata_pairs: set[tuple[str, str]] = set()

        # check if CVE ID added to errata from package' changel using EVR
        def check_cve_by_chlog(
            cve_id: str, e: Errata, changelog: PackageChangelog
        ) -> bool:
            # try to find changelog record by EVR
            for record in changelog.changelog:
                _, version, release = split_evr(record.evr)
                if (e.pkg_version, e.pkg_release) == (version, release):
                    if cve_id in vulns_from_changelog_record(record):
                        return True
            return False

        # collect existing erratas if any update is required
        for pcm in pkgs_cve_matches:
            # skip packages that filtered out before by specific package name
            if pcm.pkg_name not in pkgs_names:
                continue
            # get existing erratas by package name
            erratas = erratas_by_package.get(pcm.pkg_name, [])
            # no erratas found for current package
            if not erratas:
                continue
            # check errata contents
            for errata in erratas:
                # XXX: check errata.id is not None, just to make type-checker happy
                if errata.id is None:
                    raise ValueError("Errata ID object is 'None'")
                # skip CVE-to-Errata pairs if processed already
                if (pcm.vuln_id, errata.id.id) in processed_cve_to_errata_pairs:
                    continue
                processed_cve_to_errata_pairs.add((pcm.vuln_id, errata.id.id))
                # current CVE ID not in Errata references -> skip it
                if not is_cve_in_errata_references(pcm.vuln_id, errata):
                    continue
                # current CVE ID added to Errata by changelog -> skip it
                if check_cve_by_chlog(
                    pcm.vuln_id, errata, pkgs_changelogs[pcm.pkg_hash]
                ):
                    self.logger.debug(
                        f"{pcm.vuln_id} added to {errata.id.id} from package changelog"
                    )
                    continue
                # CVE ID from matches found in Errata' references
                # collect it for further processing
                if pcm.vuln_id not in erratas_by_cve:
                    erratas_by_cve[pcm.vuln_id] = [(errata, pcm.cpm_cpe)]
                else:
                    # skip duplicates
                    if (errata, pcm.cpm_cpe) not in erratas_by_cve[pcm.vuln_id]:
                        erratas_by_cve[pcm.vuln_id].append((errata, pcm.cpm_cpe))
                cves_by_errata_ids.setdefault(errata.id.id, set()).add(pcm.vuln_id)

        def get_errata_and_cpe(eid: str, cve: str) -> tuple[Errata, str]:
            for errata, cpe in erratas_by_cve.get(cve, []):
                # XXX: check errata.id is not None, just to make type-checker happy
                if errata.id and errata.id.id == eid:
                    return errata, cpe
            raise ValueError(f"No Errata {eid} found for {cve}")

        for eid, cves in cves_by_errata_ids.items():
            _cves = tuple(cves)
            errata, cpe = get_errata_and_cpe(eid, _cves[0])
            self.eh.add_errata_discard(
                errata=errata, cpe=cpe, cve_ids=_cves, type=self._type
            )

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
