# ALTRepo API
# Copyright (C) 2021-2026  BaseALT Ltd

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
from altrepo_api.utils import DT_NEVER

from .common.constants import (
    BDU_ID_PREFIX,
    CVE_ID_PREFIX,
    GHSA_ID_PREFIX,
    VULN_ID_TYPE2PREFIX,
)
from .common.utils import make_date_condition
from ..parsers import vuln_list_args
from ..sql import sql
from ...misc import lut


class VulnListArgs(NamedTuple):
    sort: list[str]
    is_errata: Optional[bool] = None
    input: Optional[str] = None
    severity: Optional[str] = None
    status: Optional[str] = None
    resolution: Optional[str] = None
    our: Optional[bool] = None
    limit: Optional[int] = None
    page: Optional[int] = None
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
    rejected: bool = False

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
            "rejected": self.rejected,
        }


def is_any_vuln_id(id: Optional[str]) -> bool:
    return bool(id) and (
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
        self.logger.debug(f"args: {self.args}")
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
        order_fields = [*self.args.sort, "-id"]
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
    def _severity(self) -> str:
        if self.args.severity:
            return f"severity = '{self.args.severity}'"
        return ""

    @property
    def _modified_date(self) -> str:
        if self.args.modified_start_date or self.args.modified_end_date:
            date_condition = make_date_condition(
                self.args.modified_start_date, self.args.modified_end_date
            )

            return f"modified {date_condition}"
        return ""

    @property
    def _published_date(self) -> str:
        if self.args.published_start_date or self.args.published_end_date:
            date_condition = make_date_condition(
                self.args.published_start_date, self.args.published_end_date
            )
            return f"published {date_condition}"
        return ""

    @property
    def _status(self) -> str:
        if self.args.status:
            if self.args.status == "new":
                return "(status = 'new' OR status = '')"
            else:
                return f"status = '{self.args.status}'"
        return ""

    @property
    def _resolution(self) -> str:
        if self.args.resolution:
            return f"resolution = '{self.args.resolution}'"
        return ""

    @property
    def _type(self) -> str:
        if self.args.type:
            if vuln_prefix := VULN_ID_TYPE2PREFIX.get(self.args.type):
                return f"vuln_id ILIKE '{vuln_prefix}%'"
        return ""

    @property
    def _is_errata(self) -> str:
        if self.args.is_errata:
            return "errata_ids != []"
        elif self.args.is_errata is False:
            return "errata_ids = []"
        return ""

    @property
    def _our(self) -> str:
        if self.args.our:
            return "our = 1"
        elif self.args.our is False:
            return "our = 0"
        return ""

    @property
    def _where_clause(self):
        conditions = []

        if self.args.input:
            if self.args.input.startswith("ALT-"):
                conditions.append(
                    f"arrayExists(x -> " f"(x.1 LIKE '{self.args.input}%'), errata_ids)"
                )
            elif not is_any_vuln_id(self.args.input):
                conditions.append(
                    f"arrayExists(x -> (x ILIKE '%{self.args.input}%'), cpes)"
                )

        if self._is_errata:
            conditions.append(self._is_errata)

        if self._our:
            conditions.append(self._our)

        if conditions:
            return "WHERE " + " AND ".join(conditions)
        return ""

    @property
    def _where_vuln_input(self):
        if is_any_vuln_id(self.args.input):
            return f"WHERE vuln_id ILIKE '{self.args.input}%'"
        return ""

    @property
    def _having_vulns(self):
        conditions = [
            self._modified_date,
            self._published_date,
            self._resolution,
            self._severity,
            self._status,
            self._type,
        ]

        if any(conditions):
            return "HAVING " + " AND ".join(c for c in conditions if c)
        return ""

    def get(self):
        response = self.send_sql_request(
            self.sql.get_vuln_list.format(
                where_clause=self._where_clause,
                where_vuln_input=self._where_vuln_input,
                having_vulns=self._having_vulns,
                order_by=self._order_by,
                limit=self._limit,
                page=self._page,
            )
        )

        if not self.sql_status:
            return self.error

        if not response:
            return self.store_error(
                {
                    "message": "No vulnerabilities found",
                    "args": self.args._asdict(),
                }
            )

        data = [
            VulnInfo(
                id=id,
                severity=severity,
                status=status,
                resolution=resolution,
                summary=summary,
                modified=modified,
                published=published,
                erratas=(
                    [
                        ErrataInfo(id=id, task_state=task_state)
                        for (id, task_state) in errata_ids
                    ]
                ),
                cpes=cpes,
                our=bool(our_cpes),
                rejected=bool(rejected),
            )
            for (
                id,
                severity,
                status,
                resolution,
                summary,
                modified,
                published,
                errata_ids,
                cpes,
                our_cpes,
                rejected,
                _,
            ) in response
        ]

        return (
            {
                "request_args": self.args._asdict(),
                "vulns": [el.asdict() for el in data],
            },
            200,
            {
                "Access-Control-Expose-Headers": "X-Total-Count",
                "X-Total-Count": response[0][-1],
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

            if arg.name in ("severity", "type"):
                metadata.append(
                    MetadataItem(
                        **item_info,
                        type=KnownFilterTypes.CHOICE,
                        choices=[
                            MetadataChoiceItem(value=choice, display_name=choice)
                            for choice in arg.choices
                        ],
                    )
                )

            if arg.name == "status":
                metadata.append(
                    MetadataItem(
                        **item_info,
                        type=KnownFilterTypes.NESTED_CHOICE,
                        choices=[
                            MetadataChoiceItem(
                                value=lut.vuln_status_new,
                                display_name=lut.vuln_status_new.capitalize(),
                            ),
                            MetadataChoiceItem(
                                value=lut.vuln_status_analyzing,
                                display_name=lut.vuln_status_analyzing.capitalize(),
                            ),
                            MetadataChoiceItem(
                                value=lut.vuln_status_working,
                                display_name=lut.vuln_status_working.capitalize(),
                            ),
                            MetadataChoiceItem(
                                value=lut.vuln_status_resolved,
                                display_name=lut.vuln_status_resolved.capitalize(),
                                choices=[
                                    MetadataChoiceItem(
                                        value=resolution,
                                        display_name=(
                                            resolution.replace("wont", "won't")
                                            .replace("_", " ")
                                            .capitalize()
                                        ),
                                        name="resolution",
                                        label="Resolution",
                                        help_text="Vulnerability resolution",
                                    )
                                    for resolution in lut.vuln_status_resolutions
                                ],
                            ),
                        ],
                    )
                )

        return {
            "length": len(metadata),
            "metadata": [el.asdict() for el in metadata],
        }, 200
