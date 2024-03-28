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

from functools import partial
from logging import Logger
from typing import Any, Iterable, NamedTuple, Protocol

from altrepo_api.utils import make_tmp_table_name

from .base import (
    CpeMatchVersions,
    CveCpmHashes,
    CveVersionsMatch,
    PackageTask,
    PackageVersion,
)
from .sql import SQL, sql
from ..tools.base import Errata, ErrataID, Reference, RollbackCB, UUID_T
from ..tools.changelog import ChangelogRecord, PackageChangelog, split_evr
from ..tools.constants import CVE_ID_TYPE


class _pAPIWorkerBase(Protocol):
    status: bool
    sql_status: bool
    logger: Logger

    def store_error(
        self, message: dict[str, Any], severity: int = ..., http_code: int = ...
    ) -> tuple[Any, int]: ...

    def send_sql_request(
        self, request_line: Any, http_code: int = ..., **kwargs
    ) -> Any: ...


class _pAPIWorker(_pAPIWorkerBase, Protocol):
    sql: SQL


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
            references=[Reference(rt, rl) for rt, rl in zip(el[6], el[7])],
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
            references=[Reference(rt, rl) for rt, rl in zip(el[6], el[7])],
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
) -> dict[int, list[PackageVersion]]:
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

    pkgs_versions: dict[int, list[PackageVersion]] = {}
    for p in (PackageVersion(*el) for el in response):
        pkgs_versions.setdefault(p.hash, []).append(p)

    cls.status = True
    return pkgs_versions


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
    if not cls.sql_status:
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
            id=el[0], hashes=CveCpmHashes(*el[1:4]), versions=CpeMatchVersions(*el[4:])
        )
        res.setdefault(cvm.hashes.vuln_hash, []).append(cvm)

    cls.status = True
    return res


def get_bdus_by_cves(cls: _pAPIWorker, cve_ids: Iterable[str]) -> dict[str, set[str]]:
    cls.status = False
    bdus_by_cve: dict[str, set[str]] = {}

    tmp_table = make_tmp_table_name("cve_ids")

    response = cls.send_sql_request(
        cls.sql.get_bdus_by_cves.format(tmp_table=tmp_table),
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
        bdu_id = el[0]
        for reference in (Reference(rt, rl) for rt, rl in zip(el[1], el[2])):
            if reference.type != CVE_ID_TYPE:
                continue
            bdus_by_cve.setdefault(reference.link, set()).add(bdu_id)

    cls.status = True
    return bdus_by_cve


def get_affected_errata_ids_by_transaction_id(
    cls: _pAPIWorker, transaction_id: str
) -> set[str]:
    errata_ids = set()
    cls.status = False

    response = cls.send_sql_request(
        cls.sql.get_affected_erratas_by_transaction_id.format(
            transaction_id=transaction_id
        )
    )
    if not cls.sql_status:
        return errata_ids

    for el in response:
        errata_ids.add(el[0])
        errata_ids.add(el[1])

    cls.status = True
    return errata_ids


def _wrap_delete_from(
    cls: _pAPIWorkerBase,
    sql: str,
    name: str,
    columns: list[tuple[str, str]],
    values: list[dict[str, Any]],
) -> None:
    """Wraps 'DELETE FROM' mutation SQL request using 'Memory' engine table and
    'mutations_sync' flag to handle bunch of a values that are supplied
    due to temporary and external tables are not supported by ClickHouse server."""

    cls.status = False

    _columns = ", ".join(f"{c[0]} {c[1]}" for c in columns)
    _ = cls.send_sql_request(f"CREATE TABLE {name} ({_columns}) ENGINE = Memory")
    if not cls.sql_status:
        return None

    _ = cls.send_sql_request((f"INSERT INTO {name} (*) VALUES", values))
    if not cls.sql_status:
        return None

    _ = cls.send_sql_request("SET mutations_sync = 1")
    if not cls.sql_status:
        return None

    _ = cls.send_sql_request(sql)
    if not cls.sql_status:
        return None

    _ = cls.send_sql_request("SET mutations_sync = 0")
    if not cls.sql_status:
        return None

    _ = cls.send_sql_request(f"DROP TABLE IF EXISTS {name}")
    if not cls.sql_status:
        return None


def delete_errata_history_records(cls: _pAPIWorker, errata_ids: Iterable[str]) -> None:
    cls.status = False

    tmp_table = make_tmp_table_name("errata_ids")

    _wrap_delete_from(
        cls,
        sql=cls.sql.delete_errata_history_records.format(tmp_table=tmp_table),
        name=tmp_table,
        columns=[("errata_id", "String")],
        values=[{"errata_id": e} for e in errata_ids],
    )
    if not cls.sql_status:
        return None

    cls.status = True
    return None


def delete_errata_change_history_records(
    cls: _pAPIWorker, transaction_id: UUID_T
) -> None:
    cls.status = False

    _ = cls.send_sql_request(
        cls.sql.delete_errata_change_history_records.format(
            transaction_id=str(transaction_id)
        )
    )
    if not cls.sql_status:
        return None

    cls.status = True
    return None


def delete_pnc_change_history_records(
    cls: _pAPIWorkerBase, transaction_id: UUID_T
) -> bool:
    cls.status = False

    # XXX: use 'processing.SQL' instance directly
    _ = cls.send_sql_request(
        sql.delete_pnc_change_history_records.format(transaction_id=str(transaction_id))
    )
    if not cls.sql_status:
        return False

    cls.status = True
    return True


def delete_pnc_records(cls: _pAPIWorkerBase, transaction_id: UUID_T) -> bool:
    class PncRecord(NamedTuple):
        pkg_name: str  # project_name
        pnc_result: str  # CPE string
        pnc_state: str  # state

    # collect affected `PackagesNameConversion` records
    response = cls.send_sql_request(
        sql.get_pnc_records_by_transaction_id.format(transaction_id=str(transaction_id))
    )
    if not cls.sql_status:
        return False
    if not response:
        # TODO: maybe set an error when no records found  to be deleted in DB by transaction ID
        # cls.store_error(
        #     {
        #         "message": f"Failed to get `PncCHangeHistory` records for transaction '{transaction_id}'"
        #     }
        # )
        # return False
        cls.logger.warning(
            f"No `PncCHangeHistory` records found in DB for transaction '{transaction_id}'"
        )
        return True

    tmp_table = make_tmp_table_name("pnc_records")
    pnc_records = [PncRecord(*el) for el in response]

    # delete affected `PackagesNameConversion` records
    _wrap_delete_from(
        cls,
        sql=sql.delete_pnc_records.format(tmp_table=tmp_table),
        name=tmp_table,
        columns=[
            ("pkg_name", "String"),
            ("pnc_result", "String"),
            ("pnc_state", "String"),
        ],
        values=[r._asdict() for r in pnc_records],
    )
    if not cls.sql_status:
        return False

    return True


def cpe_transaction_rollback(cls: _pAPIWorkerBase) -> RollbackCB:
    def rollback(cls: _pAPIWorkerBase, transaction_id: UUID_T) -> bool:
        # XXX: order is important here!
        # 1. delete `PackagesNameComversion` records
        status = delete_pnc_records(cls, transaction_id)
        if not status:
            return False
        # 2. delete `PncChangeHistory` records
        status = delete_pnc_change_history_records(cls, transaction_id)
        return status

    return partial(rollback, cls)
