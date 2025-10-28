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

from datetime import datetime
from typing import Iterable, NamedTuple, Union

from altrepo_api.api.misc import lut
from altrepo_api.utils import make_tmp_table_name

from .base import _pAPIWorker, _pManageErrata
from ..constants import (
    DT_NEVER,
    BUG_REFERENCE_TYPE,
    VULN_REFERENCE_TYPE,
    BDU_ID_PREFIX,
    BDU_ID_TYPE,
    BUG_ID_TYPE,
    CVE_ID_PREFIX,
    CVE_ID_TYPE,
    GHSA_ID_PREFIX,
    GHSA_ID_TYPE,
    MFSA_ID_PREFIX,
    MFSA_ID_TYPE,
)


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
        url=f"{lut.bugzilla_base}/{bug.id}",
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
    elif vuln_id.startswith(GHSA_ID_PREFIX):
        vuln_type = GHSA_ID_TYPE
        vuln_url = f"{lut.ghsa_base}/{vuln_id}"
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
