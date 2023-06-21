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

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Iterable, NamedTuple, Protocol, Union

from altrepo_api.utils import make_tmp_table_name

from ..sql import SQL


DATETIME_NEVER = datetime.fromtimestamp(0)
ERRATA_PACKAGE_UPDATE_PREFIX = "ALT-PU-"
ERRATA_BRANCH_BULLETIN_PREFIX = "ALT-BU-"


# @dataclass
class Reference(NamedTuple):
    type: str
    id: str

    def asdict(self) -> dict[str, Any]:
        return self._asdict()


# @dataclass
class Errata(NamedTuple):
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
        res = self._asdict()
        res["references"] = [r.asdict() for r in self.references]
        return res


class Vulnerability(NamedTuple):
    id: str
    type: str
    hash: str = ""
    summary: str = ""
    score: float = 0.0
    severity: str = ""
    url: str = ""
    references: list[str] = list()
    modified_date: datetime = DATETIME_NEVER
    published_date: datetime = DATETIME_NEVER
    body: str = ""
    is_valid: bool = False


class Bug(NamedTuple):
    id: int
    summary: str = ""
    is_valid: bool = False


@dataclass
class PackageUpdate:
    errata: Errata
    bugs: list[Bug]
    vulns: list[Vulnerability]

    def asdict(self) -> dict[str, Any]:
        res = self.errata.asdict()

        res["bugs"] = [bug._asdict() for bug in self.bugs]
        res["vulns"] = [vuln._asdict() for vuln in self.vulns]

        return res


@dataclass
class BranchUpdate:
    errata: Errata
    packages_updates: list[PackageUpdate]

    def asdict(self) -> dict[str, Any]:
        res = self.errata.asdict()

        res["packages_updates"] = [pu.asdict() for pu in self.packages_updates]

        return res


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
def _get_erratas(
    cls: _pAPIWorker,
    where_clause: str,
    external_tables: Union[Iterable[Any], None],
) -> Union[list[Errata], None]:
    cls.status = False

    response = cls.send_sql_request(
        cls.sql.search_valid_errata.format(where_clause=where_clause),
        external_tables=external_tables,
    )
    if not cls.sql_status:
        return None
    if not response:
        _ = cls.store_error({"message": "No errata data found in DB"})
        return None

    cls.status = True
    return [
        Errata(
            row[0],  # errata_id
            *row[1][:-1],  # errata details
            [Reference(*el) for el in row[1][-1]],  # type: ignore
        )
        for row in response
    ]


def get_erratas_by_ids(cls: _pAPIWorker, errata_ids: list[str]):
    tmp_table = make_tmp_table_name("erraia_ids")

    where_clause = cls.sql.errata_by_ids_where_clause.format(
        tmp_table=tmp_table,
    )

    external_tables = [
        {
            "name": tmp_table,
            "structure": [("errata_id", "String")],
            "data": [{"errata_id": errata_id} for errata_id in errata_ids],
        },
    ]

    return _get_erratas(cls, where_clause, external_tables)


def get_erratas_by_search_conditions(cls: _pAPIWorker, where_clause: str):
    return _get_erratas(cls, where_clause, None)


def get_vulns_by_ids(
    cls: _pAPIWorker, vuln_ids: Iterable[str]
) -> Union[list[Vulnerability], None]:
    cls.status = False

    tmp_table = make_tmp_table_name("vuln_ids")

    response = cls.send_sql_request(
        cls.sql.get_vulns_by_ids.format(tmp_table=tmp_table),
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
    return [Vulnerability(*row, is_valid=True) for row in response]


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


def get_packges_updates_erratas(
    cls: _pAPIWorker, errata_ids: list[str]
) -> Union[list[PackageUpdate], None]:
    vulns: dict[str, Vulnerability] = {}
    bugs: dict[int, Bug] = {}

    cls.status = False

    # get erratas by ids
    erratas = get_erratas_by_ids(cls, errata_ids)
    if not cls.status or erratas is None:
        return None

    # collect bugs and vulnerabilities from erratas
    for errata in erratas:
        vulns.update(
            {
                v.id: v
                for v in (
                    empty_vuln(ref.id)
                    for ref in errata.references
                    if ref.type == "vuln"
                )
            }
        )
        bugs.update(
            {
                b.id: b
                for b in (
                    Bug(id=int(ref.id))
                    for ref in errata.references
                    if ref.type == "bug"
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

    # build package update erratas result
    packages_updates: list[PackageUpdate] = []
    for errata in erratas:
        pu_bugs = [bugs[int(ref.id)] for ref in errata.references if ref.type == "bug"]
        pu_vulns = [vulns[ref.id] for ref in errata.references if ref.type == "vuln"]
        packages_updates.append(
            PackageUpdate(errata=errata, bugs=pu_bugs, vulns=pu_vulns)
        )

    cls.status = True
    return packages_updates
