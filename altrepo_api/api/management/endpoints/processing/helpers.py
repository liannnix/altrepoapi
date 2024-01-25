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

from logging import Logger
from typing import Any, Iterable, Protocol

from altrepo_api.utils import make_tmp_table_name

from .base import (
    CpeMatchVersions,
    CveCpmHashes,
    CveVersionsMatch,
    PackageTask,
    PackageVersion,
)
from .sql import SQL
from ..tools.base import Errata, ErrataID, Reference
from ..tools.changelog import ChangelogRecord, PackageChangelog, split_evr


class _pAPIWorker(Protocol):
    sql: SQL
    status: bool
    sql_status: bool
    logger: Logger

    def store_error(
        self, message: dict[str, Any], severity: int = ..., http_code: int = ...
    ) -> tuple[Any, int]:
        ...

    def send_sql_request(
        self, request_line: Any, http_code: int = ..., **kwargs
    ) -> Any:
        ...


class _pHasBranches(_pAPIWorker, Protocol):
    branches: tuple[str, ...]


def get_related_erratas_by_pkgs_names(
    cls: _pHasBranches, packages: Iterable[str], exclude_discarded: bool
) -> dict[str, Errata]:
    cls.status = False
    erratas = {}

    # collect erratas using package' names
    tmp_table = make_tmp_table_name("pkg_names")

    response = cls.send_sql_request(
        cls.sql.get_erratas_by_pkgs_names.format(
            branches=cls.branches, tmp_table=tmp_table
        ),
        external_tables=[
            {
                "name": tmp_table,
                "structure": [("pkg_name", "String")],
                "data": [{"pkg_name": n} for n in packages],
            },
        ],
    )
    if not cls.sql_status:
        return {}
    for el in response:
        errata = Errata(
            id=ErrataID.from_id(el[0]),
            created=el[1],
            updated=el[2],
            hash=el[3],
            type=el[4],
            source=el[5],
            references=[Reference(t, l) for t, l in zip(el[6], el[7])],
            pkg_hash=el[8],
            pkg_name=el[9],
            pkg_version=el[10],
            pkg_release=el[11],
            pkgset_name=el[12],
            task_id=el[13],
            subtask_id=el[14],
            task_state=el[15],
            is_discarded=bool(el[17]),
        )
        # XXX: skip discarded erratas here
        if exclude_discarded and errata.is_discarded:
            continue
        erratas[errata.id.id] = errata  # type: ignore

    cls.status = True
    return erratas


def get_related_erratas_by_cve_ids(
    cls: _pHasBranches, cve_ids: Iterable[str]
) -> dict[str, Errata]:
    cls.status = False
    erratas = {}

    tmp_table = make_tmp_table_name("cve_ids")

    response = cls.send_sql_request(
        cls.sql.get_erratas_by_cve_ids.format(
            branches=cls.branches, tmp_table=tmp_table
        ),
        external_tables=[
            {
                "name": tmp_table,
                "structure": [("cve_id", "String")],
                "data": [{"cve_id": c} for c in cve_ids],
            },
        ],
    )
    if not cls.sql_status:
        return {}
    for el in response:
        errata = Errata(
            id=ErrataID.from_id(el[0]),
            created=el[1],
            updated=el[2],
            hash=el[3],
            type=el[4],
            source=el[5],
            references=[Reference(t, l) for t, l in zip(el[6], el[7])],
            pkg_hash=el[8],
            pkg_name=el[9],
            pkg_version=el[10],
            pkg_release=el[11],
            pkgset_name=el[12],
            task_id=el[13],
            subtask_id=el[14],
            task_state=el[15],
            is_discarded=bool(el[17]),
        )
        erratas[errata.id.id] = errata  # type: ignore

    cls.status = True
    return erratas


def get_pkgs_versions(
    cls: _pAPIWorker, pkgs_hashes: Iterable[int]
) -> dict[int, PackageVersion]:
    cls.status = False

    tmp_table = make_tmp_table_name("pkgs_hashes")

    response = cls.send_sql_request(
        cls.sql.get_packages_versions.format(tmp_table=tmp_table),
        external_tables=[
            {
                "name": tmp_table,
                "structure": [("pkg_hash", "UInt64")],
                "data": [{"pkg_hash": h} for h in pkgs_hashes],
            },
        ],
    )
    if not cls.sql_status or not response:
        return {}

    cls.status = True
    return {p.hash: p for p in (PackageVersion(*el) for el in response)}


def get_pkgs_changelog(
    cls: _pAPIWorker, pkgs_hashes: Iterable[int]
) -> dict[int, PackageChangelog]:
    res: dict[int, PackageChangelog] = {}
    cls.status = False

    tmp_table = make_tmp_table_name("pkgs_hashes")

    response = cls.send_sql_request(
        cls.sql.get_packages_changelogs.format(tmp_table=tmp_table),
        external_tables=[
            {
                "name": tmp_table,
                "structure": [("pkg_hash", "UInt64")],
                "data": [{"pkg_hash": h} for h in pkgs_hashes],
            },
        ],
    )
    if not cls.sql_status or not response:
        return {}

    for el in response:
        if el[0] not in res:
            res[el[0]] = PackageChangelog(el[0], list())
        res[el[0]].changelog.append(ChangelogRecord(*el[1:]))

    cls.status = True
    return res


def get_build_tasks_by_pkg_nevr(
    cls: _pHasBranches, name: str, evr: str
) -> dict[str, list[PackageTask]]:
    """Returns dict[branch, list[PackageTask]] for given package' name and evr."""

    cls.status = False
    res: dict[str, list[PackageTask]] = {}

    epoch, version, release = split_evr(evr)

    where_clause = cls.sql.get_done_tasks_by_nevr_cluse.format(
        branches=cls.branches,
        name=name,
        epoch=epoch,
        version=version,
        release=release,
    )

    response = cls.send_sql_request(
        cls.sql.get_done_tasks.format(where_clause=where_clause)
    )
    if not cls.sql_status:
        return res

    for p in (PackageTask(*el) for el in response):
        res.setdefault(p.branch, []).append(p)

    cls.status = True
    return res


def get_pkgs_done_tasks(
    cls: _pHasBranches, pkgs_names: Iterable[str]
) -> dict[str, list[PackageTask]]:
    """Returns dict[name, list[PackageTask]] for given packages names."""

    cls.status = False
    res: dict[str, list[PackageTask]] = {}

    tmp_table = make_tmp_table_name("pkgs_names")

    where_clause = cls.sql.get_done_tasks_by_packages_clause.format(
        branches=cls.branches, tmp_table=tmp_table
    )

    response = cls.send_sql_request(
        cls.sql.get_done_tasks.format(where_clause=where_clause),
        external_tables=[
            {
                "name": tmp_table,
                "structure": [("pkg_name", "String")],
                "data": [{"pkg_name": n} for n in pkgs_names],
            },
        ],
    )
    if not cls.sql_status or not response:
        return res

    for p in (PackageTask(*el) for el in response):
        res.setdefault(p.name, []).append(p)

    cls.status = True
    return res


def get_cves_versions_matches(
    cls: _pAPIWorker, cve_cpm_hashes: Iterable[CveCpmHashes]
) -> dict[int, list[CveVersionsMatch]]:
    cls.status = False
    res: dict[int, list[CveVersionsMatch]] = {}

    tmp_table = make_tmp_table_name("pkgs_hashes")

    response = cls.send_sql_request(
        cls.sql.get_cve_versions_matches.format(tmp_table=tmp_table),
        external_tables=[
            {
                "name": tmp_table,
                "structure": [
                    ("vuln_hash", "UInt64"),
                    ("cpe_hash", "UInt64"),
                    ("cpm_version_hash", "UInt64"),
                ],
                "data": [e._asdict() for e in cve_cpm_hashes],
            },
        ],
    )
    if not cls.sql_status or not response:
        return res

    for el in response:
        cvm = CveVersionsMatch(
            id=el[0],
            hashes=CveCpmHashes(*el[1:4]),
            versions=CpeMatchVersions(*el[4:]),
        )
        res.setdefault(cvm.hashes.vuln_hash, []).append(cvm)

    cls.status = True
    return res
