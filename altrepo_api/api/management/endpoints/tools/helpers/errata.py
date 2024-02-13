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
from typing import Any, Iterable, NamedTuple, Union

from .base import _pAPIWorker, _pManageErrata
from ..base import Branch, Errata, ErrataChange, ErrataID, ErrataManageError, Reference
from ..errata_id import check_errata_id
from ..utils import convert_dt_to_timezone_aware


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
                "ec_reason": errata.reason.serialize(),
                "ec_type": errata.type.value,
                "ec_source": errata.source.value,
                "ec_origin": errata.origin.value,
                "errata_id": str(errata.errata_id),
                "transaction_id": str(errata.transaction_id),
            }

    cls.status = False

    _ = cls.send_sql_request(
        (cls.sql.store_errata_change_history, errata_change_records_gen())
    )
    if not cls.sql_status:
        return None

    cls.status = True
