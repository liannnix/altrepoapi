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

from datetime import datetime
from logging import Logger
from typing import Any, Iterable, NamedTuple, Protocol, Union

from altrepo_api.api.management.sql import SQL
from altrepo_api.utils import make_tmp_table_name
from altrepo_api.api.misc import lut

from .base import (
    Branch,
    Errata,
    ErrataChange,
    ErrataID,
    ErrataManageError,
    Task,
    TaskInfo,
    Reference,
    PncRecord,
    PncChangeRecord,
)
from .errata_id import ErrataIDService, check_errata_id
from .utils import convert_dt_to_timezone_aware
from .constants import (
    DT_NEVER,
    BUG_REFERENCE_TYPE,
    VULN_REFERENCE_TYPE,
    BDU_ID_PREFIX,
    BDU_ID_TYPE,
    BUG_ID_TYPE,
    CVE_ID_PREFIX,
    CVE_ID_TYPE,
    MFSA_ID_PREFIX,
    MFSA_ID_TYPE,
)


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


class _pHasErrataID(_pAPIWorker, Protocol):
    errata: Errata


class _pHasErrataIDService(_pAPIWorker, Protocol):
    eid_service: ErrataIDService


class _pManageErrata(_pHasErrataIDService, _pHasErrataID, Protocol):
    ...


def _sql2errata(sql_data: tuple[Any, ...]) -> Errata:
    """Converts errata history record SQL representation to Errata object."""

    class ErrataRaw(NamedTuple):
        errata_id: str
        type: str
        source: str
        created: datetime
        updated: datetime
        pkg_hash: int
        pkg_name: str
        pkg_version: str
        pkg_release: str
        pkgset_name: str
        task_id: int
        subtask_id: int
        task_state: str
        references: list[tuple[str, str]]
        hash: int
        is_discarded: int = 0

    raw = ErrataRaw(*sql_data)

    return Errata(
        id=ErrataID.from_id(raw.errata_id),
        type=raw.type,
        source=raw.source,
        created=convert_dt_to_timezone_aware(raw.created),
        updated=convert_dt_to_timezone_aware(raw.updated),
        pkg_hash=raw.pkg_hash,
        pkg_name=raw.pkg_name,
        pkg_version=raw.pkg_version,
        pkg_release=raw.pkg_release,
        pkgset_name=raw.pkgset_name,
        task_id=raw.task_id,
        subtask_id=raw.subtask_id,
        task_state=raw.task_state,
        references=[Reference(*el) for el in raw.references],
        hash=raw.hash,
        is_discarded=bool(raw.is_discarded),
    )


def is_errata_equal(first: Errata, second: Errata, fields: Iterable[str]) -> bool:
    """Checks if two errata records are equial by set of fields."""

    return tuple(getattr(first, f) for f in fields) == tuple(
        getattr(second, f) for f in fields
    )


def get_errata_contents(cls: _pManageErrata) -> None:
    """Gathers errata contents from DB to `self.errata` object."""

    cls.status = False

    where_clause = cls.sql.get_errata_by_id_where_clause.format(
        errata_id=cls.errata.id.id  # type: ignore
    )
    response = cls.send_sql_request(
        cls.sql.get_errata_info_template.format(where_clause=where_clause)
    )
    if not cls.sql_status:
        return None
    if not response:
        _ = cls.store_error(
            {"message": f"Failed to get errata info from DB for {cls.errata.id}"}
        )
        return None

    cls.errata = _sql2errata(response[0])
    cls.status = True


def get_last_errata_id_version(cls: _pManageErrata) -> Union[ErrataID, None]:
    """Checks if current errata version is the latest one."""

    cls.status = False

    if cls.errata.id is None:
        return None

    try:
        last_errata_id = check_errata_id(cls.eid_service, cls.errata.id)
    except ErrataManageError:
        _ = cls.store_error(
            {
                "message": f"Failed to check version for {cls.errata.id} by ErrataID service"
            },
            http_code=404,
        )
        return None

    if cls.errata.id < last_errata_id:
        _ = cls.store_error(
            {
                "message": f"Errata ID version is outdated: {cls.errata.id} < {last_errata_id}"
            },
            http_code=409,
        )
        return None
    elif cls.errata.id > last_errata_id:
        _ = cls.store_error(
            {
                "message": (
                    f"Errata ID version not found in DB: {cls.errata.id}. "
                    f"Lates found version is {last_errata_id}"
                )
            },
            http_code=404,
        )
        return None

    cls.status = True
    return last_errata_id


def check_errata_contents_is_changed(
    cls: _pManageErrata, errata_check_fields: Iterable[str]
) -> bool:
    """Checks if errata contents have been changed in fact."""

    last_errata_id = get_last_errata_id_version(cls)
    if not cls.status or last_errata_id is None:
        return False

    cls.status = False

    where_clause = cls.sql.get_errata_by_id_where_clause.format(
        errata_id=last_errata_id.id
    )
    response = cls.send_sql_request(
        cls.sql.get_errata_info_template.format(where_clause=where_clause)
    )
    if not cls.sql_status:
        return False
    if not response:
        _ = cls.store_error(
            {"message": f"Failed to get errata info from DB for {last_errata_id}"}
        )
        return False

    errata_from_db = _sql2errata(response[0])
    cls.status = True
    # XXX: compare errata using only hash and discard sign here due to other
    #  values except references is gathered from DB and must be consistent!
    return not is_errata_equal(cls.errata, errata_from_db, errata_check_fields)


def check_errata_is_discarded(cls: _pManageErrata) -> bool:
    """Checks whether errata was discarded already in DB."""

    cls.status = False

    if cls.errata.id is None:
        cls.logger.error(
            "Failed to check if errata is discarded: no errata id is specified"
        )
        _ = cls.store_error(
            {
                "message": "Failed to check if errata is discarded: no errata id is specified"
            }
        )
        return False

    response = cls.send_sql_request(
        cls.sql.check_errata_id_is_discarded.format(errata_id=cls.errata.id.id)
    )
    if not cls.sql_status:
        return False
    if not response:
        _ = cls.store_error(
            {"message": f"Failed to get errata info from DB for {cls.errata.id.id}"}
        )
        return False

    cls.status = True
    return response[0][0] == 1


def get_bulletin_by_package_update(
    cls: _pAPIWorker, errata_id: str
) -> Union[Errata, None]:
    """Retrieves bulletin errata record from DB by package update errata identificator."""

    cls.status = False

    where_clause = cls.sql.get_bulletin_by_pkg_update_where_clause.format(
        errata_id=errata_id
    )
    response = cls.send_sql_request(
        cls.sql.get_errata_info_template.format(where_clause=where_clause)
    )
    if not cls.sql_status:
        return None

    cls.status = True

    if response:
        return _sql2errata(response[0])

    return None


def get_bulletin_by_branch_date(
    cls: _pAPIWorker, branch_state: Branch
) -> Union[Errata, None]:
    """Retrieves bulletin errata record from DB by branch name and date."""

    cls.status = False

    where_clause = cls.sql.get_bulletin_by_branch_date__where_clause.format(
        branch=branch_state.name, date=branch_state.date
    )
    response = cls.send_sql_request(
        cls.sql.get_errata_info_template.format(where_clause=where_clause)
    )
    if not cls.sql_status:
        return None

    cls.status = True

    if response:
        return _sql2errata(response[0])

    return None


def get_errata_by_task(cls: _pManageErrata) -> Union[Errata, None]:
    """Retrieves package update errata from DB by task and subtask."""

    cls.status = False

    where_clause = cls.sql.get_errata_by_task_where_clause.format(
        task_id=cls.errata.task_id, subtask_id=cls.errata.subtask_id
    )
    response = cls.send_sql_request(
        cls.sql.get_errata_info_template.format(where_clause=where_clause)
    )
    if not cls.sql_status:
        return None

    cls.status = True

    if response:
        return _sql2errata(response[0])

    return None


def get_ec_id_by_package_update(
    cls: _pAPIWorker, errata: ErrataID
) -> Union[ErrataID, None]:
    """Retrieves errata change identificator from DB by package update errata
    identificator if exist."""

    cls.status = False

    response = cls.send_sql_request(
        cls.sql.get_ecc_by_errata_id.format(errata_id_noversion=errata.no_version)
    )
    if not cls.sql_status:
        return None

    cls.status = True

    if response:
        return ErrataID.from_id(response[0][1])

    return None


def store_errata_history_records(cls: _pAPIWorker, erratas: Iterable[Errata]) -> None:
    def errata_history_records_gen():
        for errata in erratas:
            yield {
                "errata_id": str(errata.id),
                "eh_hash": errata.hash,
                "eh_type": errata.type,
                "eh_source": errata.source,
                "eh_created": errata.created,
                "eh_updated": errata.updated,
                "eh_references.type": [r.type for r in errata.references],
                "eh_references.link": [r.link for r in errata.references],
                "pkg_hash": errata.pkg_hash,
                "pkg_name": errata.pkg_name,
                "pkg_version": errata.pkg_version,
                "pkg_release": errata.pkg_release,
                "pkgset_name": errata.pkgset_name,
                "task_id": errata.task_id,
                "subtask_id": errata.subtask_id,
                "task_state": errata.task_state,
            }

    cls.status = False

    _ = cls.send_sql_request(
        (cls.sql.store_errata_history, errata_history_records_gen())
    )
    if not cls.sql_status:
        return None

    cls.status = True


def store_errata_change_records(
    cls: _pAPIWorker, erratas: Iterable[ErrataChange]
) -> None:
    def errata_change_records_gen():
        for errata in erratas:
            yield {
                "ec_id": str(errata.id),
                "ec_created": errata.created,
                "ec_updated": errata.updated,
                "ec_user": errata.user,
                "ec_user_ip": errata.user_ip,
                "ec_reason": errata.reason,
                "ec_type": errata.type.value,
                "ec_source": errata.source.value,
                "ec_origin": errata.origin.value,
                "errata_id": str(errata.errata_id),
            }

    cls.status = False

    _ = cls.send_sql_request(
        (cls.sql.store_errata_change_history, errata_change_records_gen())
    )
    if not cls.sql_status:
        return None

    cls.status = True


def find_closest_branch_state(
    cls: _pManageErrata, task_changed: datetime
) -> Union[Branch, None]:
    """Finds closest branch state by given task."""

    cls.status = False
    branch = cls.errata.pkgset_name
    task_id = cls.errata.task_id

    # get DONE tasks history
    response = cls.send_sql_request(
        cls.sql.get_done_tasks.format(branch=branch, changed=task_changed)
    )
    if not cls.sql_status:
        return None
    if not response:
        _ = cls.store_error(
            {
                "message": f"Failed to get 'DONE' tasks history for branch {branch} from {task_id}"
            }
        )

    tasks = {t.id: t for t in (Task(*el) for el in response)}
    if task_id not in tasks:
        _ = cls.store_error(
            {
                "message": f"Task {task_id} not found in 'DONE' tasks history for {branch}"
            }
        )

    # get nearest branch point
    response = cls.send_sql_request(
        cls.sql.get_nearest_branch_point.format(branch=branch, changed=task_changed)
    )
    if not cls.sql_status:
        return None
    if not response:
        # handle this case on caller side
        cls.status = True
        return None

    branch_state = Branch(*response[0])
    if branch_state.task not in tasks:
        _ = cls.store_error(
            {"message": "Branch state is inconsistent with task history"},
            severity=cls.LL.ERROR,  # type: ignore
        )
        return None

    cls.status = True
    return branch_state


def get_last_branch_state(cls: _pManageErrata) -> Union[Branch, None]:
    """gets last branch state by given task."""

    cls.status = False
    branch = cls.errata.pkgset_name

    # get last commited branch state
    response = cls.send_sql_request(cls.sql.get_last_branch_state.format(branch=branch))
    if not cls.sql_status:
        return None
    if not response:
        _ = cls.store_error({"message": f"Failed to find last state for {branch}"})
        return None

    cls.status = True
    return Branch(*response[0])


def get_task_info(cls: _pManageErrata) -> Union[tuple[TaskInfo, datetime], None]:
    cls.status = False

    response = cls.send_sql_request(
        cls.sql.get_package_info_by_task_and_subtask.format(
            task_id=cls.errata.task_id, subtask_id=cls.errata.subtask_id
        )
    )
    if not cls.sql_status:
        return None
    if not response:
        _ = cls.store_error(
            {
                "message": "No data found in DB for given task and subtask",
                "errata": cls.errata.asdict(),
            }
        )
        return None

    cls.status = True
    return TaskInfo(*response[0][:-1]), response[0][-1]


class Vulnerability(NamedTuple):
    id: str
    type: str
    summary: str = ""
    score: float = 0.0
    severity: str = ""
    url: str = ""
    modified_date: datetime = DT_NEVER
    published_date: datetime = DT_NEVER
    references: list[str] = list()
    is_valid: bool = False


class Bug(NamedTuple):
    id: int
    summary: str = ""
    last_changed: datetime = DT_NEVER
    is_valid: bool = False


def bug2vuln(bug: Bug) -> Vulnerability:
    return Vulnerability(
        id=str(bug.id),
        type=BUG_ID_TYPE,
        summary=bug.summary,
        url=f"#{bug.id}",
        modified_date=bug.last_changed,
        published_date=bug.last_changed,
        is_valid=bug.is_valid,
    )


def empty_vuln(vuln_id: str) -> Vulnerability:
    vuln_type = ""
    if vuln_id.startswith(CVE_ID_PREFIX):
        vuln_type = CVE_ID_TYPE
        normalized_id = vuln_id.lower()
        vuln_url = f"{lut.nvd_cve_base}/{normalized_id}"
    elif vuln_id.startswith(BDU_ID_PREFIX):
        vuln_type = BDU_ID_TYPE
        normalized_id = vuln_id.removeprefix(BDU_ID_PREFIX)
        vuln_url = f"{lut.fstec_bdu_base}/{normalized_id}"
    elif vuln_id.startswith(MFSA_ID_PREFIX):
        vuln_type = MFSA_ID_TYPE
        normalized_id = vuln_id.replace("MFSA ", "mfsa").replace("MFSA-", "mfsa")
        vuln_url = f"{lut.mfsa_base}/{normalized_id}"
    else:
        vuln_url = f"#{vuln_id}"
    return Vulnerability(id=vuln_id, type=vuln_type, url=vuln_url)


def get_vulns_by_ids(
    cls: _pAPIWorker, vuln_ids: Iterable[str]
) -> Union[list[Vulnerability], None]:
    cls.status = False

    tmp_table = make_tmp_table_name("vuln_ids")

    response = cls.send_sql_request(
        cls.sql.get_vuln_info_by_ids.format(tmp_table=tmp_table),
        external_tables=[
            {
                "name": tmp_table,
                "structure": [("vuln_id", "String")],
                "data": [{"vuln_id": vuln_id} for vuln_id in vuln_ids],
            },
        ],
    )
    if not cls.sql_status:
        return None
    if response is None:
        _ = cls.store_error({"message": "No vulnerabilities data found in DB"})
        return None

    cls.status = True
    return [Vulnerability(*row[:-1], is_valid=True) for row in response]


def get_bugs_by_ids(cls: _pAPIWorker, bug_ids: Iterable[int]) -> Union[list[Bug], None]:
    cls.status = False

    tmp_table = make_tmp_table_name("bz_ids")

    response = cls.send_sql_request(
        cls.sql.get_bugs_by_ids.format(tmp_table=tmp_table),
        external_tables=[
            {
                "name": tmp_table,
                "structure": [("bz_id", "UInt32")],
                "data": [{"bz_id": bz_id} for bz_id in bug_ids],
            },
        ],
    )
    if not cls.sql_status:
        return None
    if response is None:
        _ = cls.store_error({"message": "No bugs data found in DB"})
        return None

    cls.status = True
    return [Bug(*row, is_valid=True) for row in response]


def collect_errata_vulnerabilities_info(cls: _pManageErrata):
    vulns: dict[str, Vulnerability] = {}
    bugs: dict[int, Bug] = {}

    cls.status = False

    # collect bugs and vulnerabilities from errata
    vulns.update(
        {
            v.id: v
            for v in (
                empty_vuln(ref.link)
                for ref in cls.errata.references
                if ref.type == VULN_REFERENCE_TYPE
            )
        }
    )
    bugs.update(
        {
            b.id: b
            for b in (
                Bug(id=int(ref.link))
                for ref in cls.errata.references
                if ref.type == BUG_REFERENCE_TYPE
            )
        }
    )

    # get vulnerabilities info
    vulns_data = get_vulns_by_ids(cls, (vuln_id for vuln_id in vulns))
    if not cls.status or vulns_data is None:
        return None

    vulns.update({vuln.id: vuln for vuln in vulns_data})

    # get bugs info
    bugs_data = get_bugs_by_ids(cls, (bug_id for bug_id in bugs))
    if not cls.status or bugs_data is None:
        return None

    bugs.update({bug.id: bug for bug in bugs_data})
    vulns.update({str(b_id): bug2vuln(bug) for b_id, bug in bugs.items()})

    cls.status = True
    return [vuln for vuln in vulns.values()]


def get_related_packages_by_project_name(
    cls: _pAPIWorker, project_names: list[str]
) -> list[str]:
    cls.status = False
    res = []

    tmp_table = make_tmp_table_name("project_names")

    response = cls.send_sql_request(
        cls.sql.get_packages_by_project_names.format(
            tmp_table=tmp_table,
            cpe_branches=tuple(set(lut.cpe_reverse_branch_map.keys())),
        ),
        external_tables=[
            {
                "name": tmp_table,
                "structure": [("pkg_name", "String")],
                "data": [{"pkg_name": n} for n in project_names],
            },
        ],
    )
    if not cls.sql_status:
        return []
    if response:
        res = [el[0] for el in response]

    cls.status = True
    return res


def store_pnc_records(cls: _pAPIWorker, pnc_records: list[PncRecord]) -> None:
    cls.status = False

    _ = cls.send_sql_request(
        (cls.sql.store_pnc_records, (pnc.asdict() for pnc in pnc_records))
    )
    if not cls.sql_status:
        return None

    cls.status = True
    return


def store_pnc_change_records(
    cls: _pAPIWorker, pnc_change_records: list[PncChangeRecord]
) -> None:
    def pnc_change_records_gen():
        for pncc in pnc_change_records:
            res = {
                "pncc_uuid": str(pncc.id),
                "pncc_user": pncc.user,
                "pncc_user_ip": pncc.user_ip,
                "pncc_reason": pncc.reason,
                "pncc_type": pncc.type.value,
                "pncc_source": pncc.source.value,
                "pncc_origin": pncc.origin.value,
            }
            res.update(**pncc.pnc.asdict())
            yield res

    cls.status = False

    _ = cls.send_sql_request(
        (cls.sql.store_pnc_change_records, pnc_change_records_gen())
    )
    if not cls.sql_status:
        return None

    cls.status = True


def get_pkgs_branch_and_evr_by_hashes(
    cls: _pAPIWorker, hashes: Iterable[int]
) -> dict[str, dict[str, str]]:
    class PkgInfo(NamedTuple):
        pkg_hash: str
        pkg_name: str
        pkg_version: str
        pkg_release: str
        branch: str

    cls.status = False
    res = {}

    tmp_table = make_tmp_table_name("pkg_hashes")

    response = cls.send_sql_request(
        cls.sql.get_packages_info_by_hashes.format(tmp_table=tmp_table),
        external_tables=[
            {
                "name": tmp_table,
                "structure": [("pkg_hash", "UInt64")],
                "data": [{"pkg_hash": n} for n in hashes],
            },
        ],
    )
    if not cls.sql_status:
        return {}
    for p in (PkgInfo(*el) for el in response):
        if p.pkg_hash not in res:
            res[p.pkg_hash] = p._asdict()
            res[p.pkg_hash]["branch"] = [res[p.pkg_hash]["branch"]]
        else:
            res[p.pkg_hash]["branch"].append(p.branch)

    cls.status = True
    return res
