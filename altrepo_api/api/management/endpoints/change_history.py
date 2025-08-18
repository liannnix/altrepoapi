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
import json
from dataclasses import asdict, dataclass, field
from typing import Any, Optional

from altrepo_api.api.base import APIWorker, WorkerResult
from altrepo_api.api.metadata import KnownFilterTypes, MetadataChoiceItem, MetadataItem

from ..parsers import change_history_args
from ..sql import sql
from .tools.constants import ERRATA_BRANCH_BULLETIN_PREFIX, ERRATA_PACKAGE_UPDATE_PREFIX


@dataclass
class ErrataChangeInfo:
    id: str
    errata_id: str
    created: datetime.datetime
    updated: datetime.datetime
    user: str
    reason: str
    type: str
    source: str
    vulns: list[str]
    task_id: int
    task_state: str
    deleted_vulns: list[str] = field(default_factory=list)
    added_vulns: list[str] = field(default_factory=list)


class ErrataChangeHistory(APIWorker):
    """
    Get Errata change history by ID.
    """

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def get(self):
        errata_id = self.args["errata_id"]
        ec_origin_clause = ""

        if errata_id.startswith(ERRATA_PACKAGE_UPDATE_PREFIX):
            ec_origin_clause = "AND ec_origin = 'parent'"
        if errata_id.startswith(ERRATA_BRANCH_BULLETIN_PREFIX):
            ec_origin_clause = "AND ec_origin = 'child'"

        response = self.send_sql_request(
            self.sql.get_errata_history.format(
                errata_id=errata_id, origin=ec_origin_clause
            ),
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {"message": f"No change history found for errata '{errata_id}'"}
            )
        ErrataChngHist = [ErrataChangeInfo(*el) for el in response]

        # Add a list of added vulnerabilities for the first version of the errata
        ErrataChngHist[-1].added_vulns = ErrataChngHist[-1].vulns

        # Iterate through the list until the first version of errata.
        # The list of errata is sorted by default from higher version to lower.
        for i in range(0, len(ErrataChngHist) - 1):
            # Get a lists of added and deleted vulnerabilities by comparing
            # the current errata version with the previous one.
            ErrataChngHist[i].added_vulns = [
                el
                for el in ErrataChngHist[i].vulns
                if el not in ErrataChngHist[i + 1].vulns
            ]
            ErrataChngHist[i].deleted_vulns = [
                el
                for el in ErrataChngHist[i + 1].vulns
                if el not in ErrataChngHist[i].vulns
            ]

        res = {
            "request_args": self.args,
            "length": len(ErrataChngHist),
            "history": [asdict(el) for el in ErrataChngHist],
        }
        return res, 200


@dataclass
class CpeInfo:
    cpe: str
    state: str
    project_name: str


@dataclass
class PncInfo:
    state: str
    package: str
    project_name: str


@dataclass
class Details:
    cpe: Optional[CpeInfo] = None
    pnc: Optional[PncInfo] = None
    # TODO: Group the following fields into a TaskInfo nested class, since the DB
    # contains only one of CPE, PNC, or Task-related change details at a time.
    name: Optional[str] = None
    hash: Optional[str] = None
    task_id: Optional[str] = None
    version: Optional[str] = None
    branch: Optional[str] = None
    subtask_id: Optional[str] = None
    release: Optional[str] = None
    task_state: Optional[str] = None

    def __init__(self, js: dict[str, Any]):
        if cpe := js.get("cpe"):
            self.cpe = CpeInfo(**cpe)
        if pnc := js.get("pnc"):
            self.pnc = PncInfo(**pnc)
        for key, val in js.items():
            if key in ["cpe", "pnc"]:
                continue
            setattr(self, key, val)


@dataclass
class ChangeItem:
    change_type: str
    module: str
    errata_id: Optional[str] = None
    message: Optional[str] = None
    package_name: Optional[str] = None
    result: Optional[str] = None
    details: Optional[Details] = None

    def __init__(self, js: dict[str, Any]):
        if details := js.get("details"):
            self.details = Details(json.loads(details))
        for key, val in js.items():
            if key == "details":
                continue
            setattr(self, key, val)


@dataclass
class ChangeHistoryResponse:
    event_date: datetime.datetime
    author: str
    modules: list[str]
    changes: list[ChangeItem]
    transaction_id: str


@dataclass
class ChangeHistoryArgs:
    module: Optional[str] = None
    change_type: Optional[str] = None
    user: Optional[str] = None
    input: Optional[list[str]] = None
    event_start_date: Optional[datetime.datetime] = None
    event_end_date: Optional[datetime.datetime] = None
    limit: Optional[int] = None
    page: Optional[int] = None
    sort: Optional[list[str]] = None


class ChangeHistory(APIWorker):

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = ChangeHistoryArgs(**kwargs)
        self.sql = sql
        super().__init__()

    @property
    def _limit(self) -> str:
        """
        Generate the LIMIT clause for SQL query if limit is specified.
        """
        return f"LIMIT {self.args.limit}" if self.args.limit else ""

    @property
    def _page(self) -> str:
        """
        Generate the OFFSET clause for pagination if both limit and page are specified.
        """
        if self.args.limit and self.args.page:
            page = self.args.page
            per_page = self.args.limit
            offset = (page - 1) * per_page
            return f"OFFSET {offset}"
        return ""

    @property
    def _order_by(self) -> str:
        """
        Generate the ORDER BY clause based on requested sort fields.
        """
        allowed_fields = ChangeHistoryResponse.__annotations__.keys()
        default_sorting = "ORDER BY event_date DESC"
        if not self.args.sort:
            return default_sorting

        order_clauses = []

        for sort_field in self.args.sort:
            direction = "ASC"
            field_name = sort_field

            if sort_field.startswith("-"):
                direction = "DESC"
                field_name = sort_field[1:]
            if field_name in allowed_fields:
                escaped_field = (
                    f"{field_name}" if not field_name.islower() else field_name
                )
                order_clauses.append(f"{escaped_field} {direction}, transaction_id")

        if not order_clauses:
            return default_sorting

        return f"ORDER BY {', '.join(order_clauses)}, transaction_id"

    @property
    def _create_input_conditions(self) -> list[str]:
        """Creates search conditions for the input filter."""
        if not self.args.input:
            return []
        conditions = []
        for term in self.args.input:
            # Search by errata_id and package_name
            term_conditions = [
                f"arrayExists(x -> x['errata_id'] ILIKE '%{term}%', changes)",
                f"arrayExists(x -> x['package_name'] ILIKE '%{term}%', changes)",
                f"arrayExists(x -> x['details'] ILIKE '%{term}%', changes)",
            ]
            conditions.append(f"({' OR '.join(term_conditions)})")

        return conditions

    @property
    def _where_clause(self):
        conditions = []

        # Filter by module (array contains)
        if self.args.module != "all":
            conditions.append(f"has(modules, '{self.args.module}')")

        # Filter by user (exact match)
        if self.args.user:
            conditions.append(f"author = '{self.args.user}'")

        # Filter by change type
        if self.args.change_type != "all":
            conditions.append(
                f"arrayExists(x -> x['change_type'] = '{self.args.change_type}', changes)"
            )

        # Filter by date range
        if self.args.event_start_date:
            conditions.append(
                f"event_date >= '{self.args.event_start_date.isoformat()}'"
            )
        if self.args.event_end_date:
            conditions.append(f"event_date <= '{self.args.event_end_date.isoformat()}'")

        # Filter by input
        conditions.extend(self._create_input_conditions)

        # Combine all conditions
        if conditions:
            return "WHERE " + " AND ".join(conditions)
        return ""

    def get(self) -> WorkerResult:
        response = self.send_sql_request(
            self.sql.get_change_history.format(
                where_clause=self._where_clause,
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
                    "message": "No change history data found for given parameters",
                    "args": asdict(self.args),
                }
            )
        total_count = response[0][-1]
        changes = [
            ChangeHistoryResponse(
                event_date=hist[0],
                author=hist[1],
                modules=hist[2],
                changes=[ChangeItem(change) for change in hist[3]],
                transaction_id=hist[4],
            )
            for hist in response
        ]
        res: dict[str, Any] = {
            "request_args": asdict(self.args),
            "length": len(changes),
            "change_history": [asdict(el) for el in changes],
        }
        return (
            res,
            200,
            {
                "Access-Control-Expose-Headers": "X-Total-Count",
                "X-Total-Count": total_count,
            },
        )

    def metadata(self) -> WorkerResult:
        metadata = []
        for el in change_history_args.args:
            is_append = False
            meta = MetadataItem(
                name=el.name,
                label=el.name.replace("_", " ").capitalize(),
                help_text=el.help,
                type=KnownFilterTypes.STRING,
            )
            if el.type.__name__ == "date_string_type":
                meta.type = KnownFilterTypes.DATE
                is_append = True
            if el.name in ["module", "change_type"]:
                meta.type = KnownFilterTypes.CHOICE
                meta.choices = [
                    MetadataChoiceItem(value=choice, display_name=choice.capitalize())
                    for choice in el.choices
                    if choice != "all"
                ]
                is_append = True
            if el.name == "user":
                users = self.send_sql_request(self.sql.get_authors_change_history)
                if users:
                    meta.type = KnownFilterTypes.CHOICE
                    meta.choices = [
                        MetadataChoiceItem(value=user[0], display_name=user[0])
                        for user in users
                    ]
                    is_append = True
            if is_append:
                metadata.append(meta)
        return {
            "length": len(metadata),
            "metadata": [el.asdict() for el in metadata],
        }, 200
