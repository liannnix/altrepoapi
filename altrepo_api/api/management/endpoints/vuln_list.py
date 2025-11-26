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
from typing import Any, NamedTuple, Optional

from altrepo_api.api.base import APIWorker, WorkerResult
from altrepo_api.api.metadata import KnownFilterTypes, MetadataChoiceItem, MetadataItem
from altrepo_api.utils import make_tmp_table_name

from .tools.constants import (
    BDU_ID_PREFIX,
    CVE_ID_PREFIX,
    DT_NEVER,
    GHSA_ID_PREFIX,
    VULN_ID_TYPE2PREFIX,
)
from .tools.utils import make_date_condition
from ..parsers import vuln_list_args
from ..sql import sql


class VulnListArgs(NamedTuple):
    is_errata: bool
    input: Optional[str] = None
    severity: Optional[str] = None
    status: Optional[str] = None
    resolution: Optional[str] = None
    our: Optional[bool] = None
    limit: Optional[int] = None
    page: Optional[int] = None
    sort: Optional[list[str]] = None
    modified_start_date: Optional[datetime] = None
    modified_end_date: Optional[datetime] = None
    published_start_date: Optional[datetime] = None
    published_end_date: Optional[datetime] = None
    type: Optional[str] = None


class ErrataInfo(NamedTuple):
    id: str
    task_state: str


class VulnInfo(NamedTuple):
    id: str = ""
    severity: str = ""
    status: str = ""
    resolution: Optional[str] = None
    summary: str = ""
    modified: datetime = DT_NEVER
    published: datetime = DT_NEVER
    erratas: list[ErrataInfo] = []
    cpes: list[str] = []
    our: bool = False

    def asdict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "severity": self.severity,
            "status": self.status,
            "resolution": self.resolution,
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
        self.kwargs = kwargs
        self.args: VulnListArgs
        self.status: bool = False
        self.vulns: dict[str, VulnInfo] = {}
        self.total_count: int
        self.sql = sql
        super().__init__()

    def check_params(self) -> bool:
        self.args = VulnListArgs(**self.kwargs)
        self.logger.debug(f"args: {self.kwargs}")
        return True

    @property
    def _limit(self) -> str:
        return f"LIMIT {self.args.limit}" if self.args.limit else ""

    @property
    def _page(self) -> str:
        if self.args.limit and self.args.page:
            page = self.args.page
            per_page = self.args.limit
            offset = (page - 1) * per_page
            return f"OFFSET {offset}"
        return ""

    @property
    def _order_by(self) -> str:
        order_fields = self.args.sort or ["modified"]
        order_clauses = []

        for sort_field in order_fields:
            direction = "ASC"
            field_name = sort_field

            if sort_field.startswith("-"):
                direction = "DESC"
                field_name = sort_field.removeprefix("-")
            if field_name in VulnInfo._fields:
                order_clauses.append(f"{field_name} {direction}")

        return "ORDER BY " + ", ".join(order_clauses)

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

        if self.args.modified_start_date or self.args.modified_end_date:
            date_condition = make_date_condition(
                self.args.modified_start_date, self.args.modified_end_date
            )

            where_clause += (
                f" AND VULNS.modified {date_condition}"
                if where_clause
                else f"WHERE VULNS.modified {date_condition}"
            )

        if self.args.published_start_date or self.args.published_end_date:
            date_condition = make_date_condition(
                self.args.published_start_date, self.args.published_end_date
            )

            where_clause += (
                f" AND VULNS.published {date_condition}"
                if where_clause
                else f"WHERE VULNS.published {date_condition}"
            )

        if self.args.status:
            where_clause += (
                f" AND VULNS.status = '{self.args.status}'"
                if where_clause
                else f"WHERE VULNS.status =  '{self.args.status}'"
            )

        if self.args.resolution:
            where_clause += (
                f" AND VULNS.resolution = '{self.args.resolution}'"
                if where_clause
                else f"WHERE VULNS.resolution = '{self.args.resolution}'"
            )

        if self.args.type and self.args.type != "all":
            if vuln_prefix := VULN_ID_TYPE2PREFIX.get(self.args.type):
                where_clause += (
                    f"AND VULNS.vuln_id ILIKE '{vuln_prefix}%'"
                    if where_clause
                    else f"WHERE VULNS.vuln_id ILIKE '{vuln_prefix}%'"
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
                where_clause=self._where_vuln,
                where_clause2=where_clause,
                order_by=self._order_by,
                limit=self._limit,
                page=self._page,
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

        self.total_count = response[0][-1]
        if self.vulns:
            self.vulns = {
                vuln_id: VulnInfo(
                    vuln_id,
                    *body,
                    erratas=self.vulns[vuln_id].erratas,
                    cpes=self.vulns[vuln_id].cpes,
                    our=self.vulns[vuln_id].our,
                )
                for vuln_id, *body, _ in response
            }
        else:
            self.vulns = {
                vuln_id: VulnInfo(vuln_id, *body) for vuln_id, *body, _ in response
            }
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

        return (
            {
                "request_args": self.args._asdict(),
                "length": len(vulns),
                "vulns": vulns,
            },
            200,
            {
                "Access-Control-Expose-Headers": "X-Total-Count",
                "X-Total-Count": self.total_count,
            },
        )

    def metadata(self) -> WorkerResult:
        metadata = []
        for arg in vuln_list_args.args:
            item_info = {
                "name": arg.name,
                "label": arg.name.replace("_", " ").capitalize(),
                "help_text": arg.help,
            }
            if arg.type.__name__ == "date_string_type":
                metadata.append(MetadataItem(**item_info, type=KnownFilterTypes.DATE))

            if arg.type.__name__ == "boolean":
                metadata.append(
                    MetadataItem(
                        **item_info,
                        type=KnownFilterTypes.CHOICE,
                        choices=[
                            MetadataChoiceItem(value="true", display_name="True"),
                            MetadataChoiceItem(value="false", display_name="False"),
                        ],
                    )
                )

            if arg.name in ("severity", "status", "type"):
                metadata.append(
                    MetadataItem(
                        **item_info,
                        type=KnownFilterTypes.CHOICE,
                        choices=[
                            MetadataChoiceItem(
                                value=choice, display_name=choice.capitalize()
                            )
                            for choice in arg.choices
                        ],
                    )
                )

            if arg.name == "resolution":
                metadata.append(
                    MetadataItem(
                        **item_info,
                        type=KnownFilterTypes.CHOICE,
                        choices=[
                            MetadataChoiceItem(
                                value=resolution,
                                display_name=(
                                    resolution.replace("wont", "won't")
                                    .replace("_", " ")
                                    .capitalize()
                                ),
                            )
                            for resolution in arg.choices
                        ],
                    )
                )

        return {
            "length": len(metadata),
            "metadata": [el.asdict() for el in metadata],
        }, 200
