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

from logging import Logger
from typing import Any, Iterable, Protocol, Union

from altrepo_api.api.management.sql import SQL

from .base import Errata, ErrataChange, ErrataID, ErrataManageError, Reference
from .errata_id import ErrataIDService, check_errata_id


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


def get_last_errata_id_version(cls: _pManageErrata) -> Union[ErrataID, None]:
    """Checks if current errata version is the latest one."""

    cls.status = False

    if cls.errata.id is None:
        return

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


def check_errata_contents_is_changed(cls: _pManageErrata) -> bool:
    """Checks if errata contents have been changed in fact."""

    last_errata_id = get_last_errata_id_version(cls)
    if not cls.status or last_errata_id is None:
        return False

    cls.status = False

    response = cls.send_sql_request(
        cls.sql.get_errata_info.format(errata_id=last_errata_id.id)
    )
    if not cls.sql_status:
        return False
    if not response:
        _ = cls.store_error(
            {"message": f"Failed to get errata info from DB for {last_errata_id}"}
        )
        return False

    r = response[0]
    errata_from_db = Errata(
        ErrataID.from_id(r[0]), *r[1:-2], [Reference(*el) for el in r[-2]], r[-1]  # type: ignore
    )

    cls.status = True
    return cls.errata.hash != errata_from_db.hash


def get_bulletin_by_package_update(
    cls: _pAPIWorker, errata_id: str
) -> Union[Errata, None]:
    """Retrieves bulletin errata record from DB by package update errata identificator."""

    cls.status = False

    response = cls.send_sql_request(
        cls.sql.get_bulletin_by_pkg_update.format(errata_id=errata_id)
    )
    if not cls.sql_status:
        return None

    cls.status = True

    if response:
        r = response[0]
        return Errata(
            ErrataID.from_id(r[0]), *r[1:-2], [Reference(*el) for el in r[-2]], r[-1]  # type: ignore
        )

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
