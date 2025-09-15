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


from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Optional

from altrepo_api.api.base import APIWorker, WorkerResult
from altrepo_api.api.metadata import KnownFilterTypes, MetadataChoiceItem, MetadataItem
from altrepo_api.utils import get_logger

from ..parsers import default_reasons_list_args
from ..sql import sql

logger = get_logger(__name__)


@dataclass
class DefaultReasonResponse:
    text: str
    source: str
    is_active: bool
    updated: datetime


@dataclass
class DefaultReasonsArgs:
    text: Optional[str] = None
    source: Optional[str] = None
    is_active: Optional[bool] = None
    limit: Optional[int] = None
    page: Optional[int] = None
    sort: Optional[list[str]] = None


class DefaultReasonsList(APIWorker):
    """
    Get a list of all default reasons from the database.
    """

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = DefaultReasonsArgs(**kwargs)
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
        allowed_fields = DefaultReasonResponse.__annotations__.keys()
        default_sorting = "ORDER BY updated DESC"
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
                order_clauses.append(f"{escaped_field} {direction}")

        if not order_clauses:
            return default_sorting

        return f"ORDER BY {', '.join(order_clauses)}"

    @property
    def _create_text_condition(self) -> str:
        """Creates search condition for the text filter."""
        if self.args.text:
            return f"dr_text ILIKE '%{self.args.text}%'"
        return ""

    @property
    def _create_source_condition(self) -> str:
        """Creates search condition for the source filter."""
        if self.args.source:
            return f"dr_source = '{self.args.source}'"
        return ""

    @property
    def _having_clause(self) -> str:
        """Creates search condition for the is_active filter"""
        if self.args.is_active is not None:
            return f"HAVING dr_is_active = {int(self.args.is_active)}"
        return ""

    @property
    def _where_clause(self) -> str:
        conditions = []

        if self._create_source_condition:
            conditions.append(self._create_source_condition)

        if self._create_text_condition:
            conditions.append(self._create_text_condition)

        if conditions:
            return "WHERE " + " AND ".join(conditions)
        return ""

    def get(self):
        """
        Get a list of default reasons.
        """
        response = self.send_sql_request(
            self.sql.get_default_reasons_list.format(
                where_clause=self._where_clause,
                having_clause=self._having_clause,
                limit=self._limit,
                offset=self._page,
                order_by=self._order_by,
            )
        )

        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {
                    "message": "No default reasons found",
                    "args": asdict(self.args),
                }
            )

        total_count = response[0][-1]

        reasons = [
            DefaultReasonResponse(
                text=el[0], source=el[1], is_active=bool(el[2]), updated=el[3]
            )
            for el in response
        ]

        return (
            {
                "request_args": asdict(self.args),
                "length": len(reasons),
                "reasons": [asdict(el) for el in reasons],
            },
            200,
            {
                "Access-Control-Expose-Headers": "X-Total-Count",
                "X-Total-Count": total_count,
            },
        )

    def metadata(self) -> WorkerResult:
        metadata = []
        for el in default_reasons_list_args.args:
            is_append = False
            meta = MetadataItem(
                name=el.name,
                label=el.name.replace("_", " ").capitalize(),
                help_text=el.help,
                type=KnownFilterTypes.STRING,
            )
            if el.name == "text":
                is_append = True
            if el.name == "source":
                meta.type = KnownFilterTypes.CHOICE
                meta.choices = [
                    MetadataChoiceItem(value=choice, display_name=choice.capitalize())
                    for choice in el.choices
                ]
                is_append = True
            if el.name == "is_active":
                meta.type = KnownFilterTypes.CHOICE
                meta.choices = [
                    MetadataChoiceItem(value="true", display_name="True"),
                    MetadataChoiceItem(value="false", display_name="False"),
                ]
                is_append = True
            if is_append:
                metadata.append(meta)
        return {
            "length": len(metadata),
            "metadata": [el.asdict() for el in metadata],
        }, 200
