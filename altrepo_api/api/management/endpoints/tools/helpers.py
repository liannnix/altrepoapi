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
from typing import Any, Iterable, Protocol

from altrepo_api.api.management.sql import SQL

from .base import Errata


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

    # FIXME: mocked up
    # _ = cls.send_sql_request(
    #     (cls.sql.store_errata_history, errata_history_records_gen())
    # )
    # if not cls.sql_status:
    #     return None
    for r in errata_history_records_gen():
        print("DBG", r)

    cls.status = True
