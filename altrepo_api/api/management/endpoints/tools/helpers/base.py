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

from logging import Logger
from typing import Any, Protocol

from altrepo_api.api.management.sql import SQL

from ..base import Errata
from ..errata_id import ErrataIDServiceProtocol


class _pAPIWorker(Protocol):
    sql: SQL
    status: bool
    sql_status: bool
    logger: Logger

    def store_error(
        self, message: dict[str, Any], severity: int = ..., http_code: int = ...
    ) -> tuple[Any, int]: ...

    def send_sql_request(
        self, request_line: Any, http_code: int = ..., **kwargs
    ) -> Any: ...


class _pHasErrataID(_pAPIWorker, Protocol):
    errata: Errata


class _pHasErrataIDService(_pAPIWorker, Protocol):
    eid_service: ErrataIDServiceProtocol


class _pManageErrata(_pHasErrataIDService, _pHasErrataID, Protocol): ...
