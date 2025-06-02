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

import datetime

from typing import Any, NamedTuple, Union

from altrepo_api.api.base import APIWorker
from altrepo_api.libs.pagination import Paginator
from altrepo_api.libs.sorting import rich_sort
from altrepo_api.utils import make_tmp_table_name

from .tools.constants import BDU_ID_PREFIX, CVE_ID_PREFIX, DT_NEVER, GHSA_ID_PREFIX
from ..sql import sql


class VulnListArgs(NamedTuple):
    input: Union[str, None]
    severity: Union[str, None]
    is_errata: bool
    our: Union[bool, None]
    limit: Union[int, None]
    page: Union[int, None]
    sort: Union[list[str], None]
    modified_start_date: Union[datetime.datetime, None]
    modified_end_date: Union[datetime.datetime, None]
    published_start_date: Union[datetime.datetime, None]
    published_end_date: Union[datetime.datetime, None]


class ErrataInfo(NamedTuple):
    id: str
    task_state: str


class VulnInfo(NamedTuple):
    id: str = ""
    severity: str = ""
    summary: str = ""
    modified: datetime.datetime = DT_NEVER
    published: datetime.datetime = DT_NEVER
    erratas: list[ErrataInfo] = []
    cpes: list[str] = []
    our: bool = False

    def asdict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "severity": self.severity,
            "summary": self.summary,
            "modified": self.modified,
            "published": self.published,
            "erratas": [el._asdict() for el in self.erratas],
            "cpes": self.cpes,
            "our": self.our,
        }


def is_any_vuln_id(id: str) -> bool:
    return (
        id.startswith(CVE_ID_PREFIX)
        or id.startswith(BDU_ID_PREFIX)
        or id.startswith(GHSA_ID_PREFIX)
    )


class VulnList(APIWorker):
    """
    Get a list of all vulnerabilities from the database.
    """

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args: VulnListArgs = VulnListArgs(**kwargs)
        self.status: bool = False
        self.vulns: dict[str, VulnInfo] = {}
        self.sql = sql
        super().__init__()

    @property
    def _where_vuln(self) -> str:
        """
        Search conditions for vulnerabilities.
        """
        where_clause = (
            f"WHERE severity = '{self.args.severity}'" if self.args.severity else ""
        )
        where_clause += (
            (
                f" AND vuln_id ILIKE '{self.args.input}%'"
                if where_clause
                else f"WHERE vuln_id ILIKE '{self.args.input}%'"
            )
            if self.args.input and is_any_vuln_id(self.args.input)
            else ""
        )

        if self.args.modified_start_date and self.args.modified_end_date:
            date_condition = self._make_date_condition(
                self.args.modified_start_date, self.args.modified_end_date
            )

            where_clause += (
                f" AND VULNS.modified {date_condition}"
                if where_clause
                else f"WHERE VULNS.modified {date_condition}"
            )

        if self.args.published_start_date and self.args.published_end_date:
            date_condition = self._make_date_condition(
                self.args.published_start_date, self.args.published_end_date
            )

            where_clause += (
                f" AND VULNS.published {date_condition}"
                if where_clause
                else f"WHERE VULNS.published {date_condition}"
            )

        return where_clause

    @property
    def _where_errata(self) -> str:
        """
        Search conditions for erratas and CPE records.
        """
        where_clause = ""
        if self.args.input:
            if self.args.input.startswith("ALT-"):
                where_clause = (
                    f"WHERE arrayExists(x -> "
                    f"(x.1 LIKE '{self.args.input}%'), errata_ids)"
                )
            elif not is_any_vuln_id(self.args.input):
                where_clause = (
                    f"WHERE arrayExists(x -> (x ILIKE '%{self.args.input}%'), cpes)"
                )
        if self.args.is_errata:
            where_clause += (
                "WHERE errata_ids != []"
                if not where_clause
                else " AND errata_ids != []"
            )
        if self.args.our is not None:
            operator = "WHERE" if not where_clause else " AND"
            where_clause += (
                f"{operator} our = 1"
                if self.args.our is True
                else f"{operator} our = 0 AND errata_ids = []"
            )
        return where_clause

    def _make_date_condition(self, start: str, end: str) -> str:
        """
        Make date range condition for a field.
        """
        if start and end:
            return f" BETWEEN '{start}' AND '{end}' "
        elif start:
            return f" >= '{start}' "
        elif end:
            return f" <= '{end}' "
        return ""

    def _get_vulnerability_list(self):
        """
        Get all vulnerabilities.
        """
        self.status = False

        _tmp_table = "vuln_ids"
        where_clause = (
            (
                f"WHERE vuln_id in {_tmp_table}"
                if not self._where_vuln
                else f" AND vuln_id in {_tmp_table}"
            )
            if self.vulns
            else ""
        )
        response = self.send_sql_request(
            self.sql.get_vuln_list.format(
                where_clause=self._where_vuln, where_clause2=where_clause
            ),
            external_tables=[
                {
                    "name": _tmp_table,
                    "structure": [
                        ("id", "String"),
                    ],
                    "data": [{"id": vuln} for vuln in self.vulns.keys()],
                }
            ],
        )
        if not response:
            _ = self.store_error(
                {
                    "message": "No vulnerabilities found",
                    "args": self.args._asdict(),
                }
            )
            return None
        if not self.sql_status:
            return None

        if self.vulns:
            self.vulns = {
                el[0]: VulnInfo(
                    *el,
                    erratas=self.vulns[el[0]].erratas,
                    cpes=self.vulns[el[0]].cpes,
                    our=self.vulns[el[0]].our,
                )
                for el in response
            }
        else:
            self.vulns = {el[0]: VulnInfo(*el) for el in response}
        self.status = True

    def _get_erratas_and_cpes(self, first: bool = False):
        """
        Get a list of errata and CPE records for the vulnerability.
        """
        self.status = False

        tmp_table = make_tmp_table_name("vuln_ids")
        where_clause = f"WHERE vuln_id in {tmp_table}" if self.vulns else ""
        response = self.send_sql_request(
            self.sql.get_erratas_vuln.format(
                where_clause1=where_clause,
                where_clause2=self._where_errata,
            ),
            external_tables=[
                {
                    "name": tmp_table,
                    "structure": [
                        ("id", "String"),
                    ],
                    "data": [{"id": vuln} for vuln in self.vulns.keys()],
                }
            ],
        )
        if not self.sql_status:
            return None

        if first and not response:
            if not response:
                _ = self.store_error(
                    {
                        "message": "No vulnerabilities found",
                        "args": self.args._asdict(),
                    }
                )
                return None
        if response:
            if self.vulns:
                for el in response:
                    self.vulns[el[0]] = self.vulns[el[0]]._replace(
                        erratas=[ErrataInfo(*errata) for errata in el[1]],
                        cpes=el[2],
                        our=True if el[1] else el[3],
                    )
            else:
                self.vulns = {
                    el[0]: VulnInfo(
                        erratas=[ErrataInfo(*errata) for errata in el[1]],
                        cpes=el[2],
                        our=True if el[1] else el[3],
                    )
                    for el in response
                }
        self.status = True

    def get(self):
        # if filters related to errata or cpe are installed,
        # then first execute the `_get_erratas_and_cpes` method
        if (
            (self.args.input and not is_any_vuln_id(self.args.input))
            or self.args.is_errata
            or self.args.our is not None
        ):
            self._get_erratas_and_cpes(True)
            if not self.status:
                return self.error
            self._get_vulnerability_list()
            if not self.status:
                return self.error
        else:
            self.vulns: dict[str, VulnInfo] = {}
            self._get_vulnerability_list()
            if not self.status:
                return self.error
            self._get_erratas_and_cpes()
            if not self.status:
                return self.error

        vulns = [el.asdict() for el in self.vulns.values()]

        if self.args.sort:
            vulns = rich_sort(vulns, self.args.sort)

        paginator = Paginator(vulns, self.args.limit)
        page_obj = paginator.get_page(self.args.page)

        res: dict[str, Any] = {
            "request_args": self.args._asdict(),
            "length": len(page_obj),
            "vulns": page_obj,
        }

        return (
            res,
            200,
            {
                "Access-Control-Expose-Headers": "X-Total-Count",
                "X-Total-Count": int(paginator.count),
            },
        )
