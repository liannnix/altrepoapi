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

import logging

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterable, NamedTuple, Protocol, Union

from altrepo_api.utils import make_tmp_table_name
from altrepo_api.api.misc import lut

from ..sql import SQL


DATETIME_NEVER = datetime.fromtimestamp(0)
ERRATA_PACKAGE_UPDATE_PREFIX = f"{lut.errata_package_update_prefix}-"
ERRATA_BRANCH_BULLETIN_PREFIX = f"{lut.errata_branch_update_prefix}-"
PACKAGE_UPDATE_MAX_BATCH = 1000
BRANCH_UPDATE_MAX_BATCH = 1000
BDU_ID_TYPE = "BDU"
BDU_ID_PREFIX = f"{BDU_ID_TYPE}:"
CVE_ID_TYPE = "CVE"
CVE_ID_PREFIX = f"{CVE_ID_TYPE}-"
MFSA_ID_TYPE = "MFSA"
MFSA_ID_PREFIX = f"{MFSA_ID_TYPE}"
RT_BUG = lut.errata_ref_type_bug
RT_VULN = lut.errata_ref_type_vuln


# @dataclass
class Reference(NamedTuple):
    type: str
    id: str

    def asdict(self) -> dict[str, Any]:
        return self._asdict()


class ErrataID(NamedTuple):
    """ErrataID object class"""

    id: str
    prefix: str
    year: int
    number: int
    version: int

    @staticmethod
    def from_id(id: str) -> "ErrataID":
        """Creates an ErrataID object from string representation."""

        # TODO: we assume that `errata id` string representation is always validated
        # before used to build `ErrataID` instance here
        # if not re_errata_id.fullmatch(id):
        #     raise ErrataIDInvalidError(f"Not a valid Errata ID: {id}")

        _parts = id.split("-")

        return ErrataID(
            id=id,
            prefix="-".join(_parts[:2]),
            year=int(_parts[2]),
            number=int(_parts[3]),
            version=int(_parts[4]),
        )

    def __str__(self):
        return self.id

    @property
    def _compare_key(self):
        """ErrataID object comparison key that excludes prefix."""
        return (self.year, self.number, self.version)

    def _compare(self, other: "ErrataID", method) -> bool:
        if not isinstance(other, ErrataID):
            return NotImplemented

        return method(self._compare_key, other._compare_key)

    def __eq__(self, other: "ErrataID") -> bool:
        return self._compare(other, lambda s, o: s == o)

    def __ne__(self, other: "ErrataID") -> bool:
        return self._compare(other, lambda s, o: s != o)

    def __lt__(self, other: "ErrataID") -> bool:
        return self._compare(other, lambda s, o: s < o)

    def __le__(self, other: "ErrataID") -> bool:
        return self._compare(other, lambda s, o: s <= o)

    def __gt__(self, other: "ErrataID") -> bool:
        return self._compare(other, lambda s, o: s > o)

    def __ge__(self, other: "ErrataID") -> bool:
        return self._compare(other, lambda s, o: s >= o)

    @property
    def no_version(self) -> str:
        return f"{self.prefix}-{self.year}-{self.number}"


class Errata(NamedTuple):
    id: ErrataID
    type: str
    source: str
    created: datetime
    updated: datetime
    pkg_hash: str
    pkg_name: str
    pkg_version: str
    pkg_release: str
    pkgset_name: str
    task_id: int
    subtask_id: int
    task_state: str
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


# Protocols
class _pAPIWorker(Protocol):
    sql: SQL
    status: bool
    sql_status: bool
    logger: logging.Logger

    def store_error(
        self, message: dict[str, Any], severity: int = ..., http_code: int = ...
    ) -> tuple[Any, int]: ...

    def send_sql_request(
        self, request_line: Any, http_code: int = ..., **kwargs
    ) -> Any: ...


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
        errata
        for errata in sorted(
            (
                Errata(
                    # row[0],  # errata_id_noversion
                    ErrataID.from_id(row[1][0]),
                    *row[1][1:-1],  # errata details
                    [Reference(*el) for el in row[1][-1]],  # type: ignore
                    # row[2],  # eh_updated
                )
                for row in response
            ),
            key=lambda x: x.id,
            reverse=True,
        )
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
                    if ref.type == RT_VULN
                )
            }
        )
        bugs.update(
            {
                b.id: b
                for b in (
                    Bug(id=int(ref.id))
                    for ref in errata.references
                    if ref.type == RT_BUG
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
        pu_bugs = [bugs[int(ref.id)] for ref in errata.references if ref.type == RT_BUG]
        pu_vulns = [vulns[ref.id] for ref in errata.references if ref.type == RT_VULN]
        packages_updates.append(
            PackageUpdate(errata=errata, bugs=pu_bugs, vulns=pu_vulns)
        )

    cls.status = True
    return packages_updates
