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

import logging

from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from typing import Any, Protocol

from ..sql import SQL


DATETIME_NEVER = datetime.fromtimestamp(0)


@dataclass
class Reference:
    type: str
    id: str

    def asdict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Errata:
    id: str
    type: str
    source: str
    pkg_hash: str
    pkg_name: str
    pkg_version: str
    pkg_release: str
    pkgset_name: str
    pkgset_date: date
    task_id: int
    subtask_id: int
    task_state: str
    task_changed: date
    references: list[Reference]

    def asdict(self) -> dict[str, Any]:
        res = asdict(self)
        res["references"] = [r.asdict() for r in self.references]
        return res


@dataclass
class Vulnerability:
    id: str
    type: str
    hash: str = ""
    summary: str = ""
    score: float = 0.0
    severity: str = ""
    url: str = ""
    references: list[str] = field(default_factory=list)
    modified_date: datetime = DATETIME_NEVER
    published_date: datetime = DATETIME_NEVER
    body: str = ""
    is_valid: bool = False


@dataclass
class Bug:
    id: int
    summary: str = ""
    is_valid: bool = False


@dataclass
class PackageUpdate(Errata):
    bugs: list[Bug]
    vulns: list[Vulnerability]


@dataclass
class BranchUpdate(Errata):
    packages_updates: list[PackageUpdate]


def empty_vuln(vuln_id: str) -> Vulnerability:
    vuln_type = ""
    if vuln_id.startswith("CVE-"):
        vuln_type = "CVE"
    elif vuln_id.startswith("BDU:"):
        vuln_type = "BDU"
    return Vulnerability(id=vuln_id, type=vuln_type)


# Protocols
class _pAPIWorker(Protocol):
    sql: SQL
    status: bool
    sql_status: bool
    logger: logging.Logger

    def store_error(
        self, message: dict[str, Any], severity: int = ..., http_code: int = ...
    ) -> tuple[Any, int]:
        ...

    def send_sql_request(
        self, request_line: Any, http_code: int = ..., **kwargs
    ) -> Any:
        ...


# Mixin
def get_erratas(cls: _pAPIWorker, where_clause: str) -> None:
    cls.status = False

    pass

    cls.status = True
