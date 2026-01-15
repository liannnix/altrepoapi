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
from typing import NamedTuple, Optional

from altrepo_api.api.base import APIWorker, WorkerResult
from altrepo_api.api.metadata import KnownFilterTypes, MetadataChoiceItem, MetadataItem
from altrepo_api.utils import get_logger

from .common.constants import DEFAULT_REASON_ACTION_TYPES
from ..parsers import default_reasons_list_args
from ..sql import sql

logger = get_logger(__name__)


class DefaultReasonResponse(NamedTuple):
    text: str
    source: str
    action: str
    is_active: bool
    updated: datetime


class DefaultReasonsArgs(NamedTuple):
    text: Optional[str] = None
    source: Optional[str] = None
    action: Optional[list[str]] = None
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
        self.kwargs = kwargs
        self.args: DefaultReasonsArgs
        self.sql = sql
        super().__init__()

    def check_params(self) -> bool:
        self.args = DefaultReasonsArgs(**self.kwargs)
        self.logger.debug(f"args : {self.kwargs}")
        actions = self.args.action
        if actions is None:
            return True

        for action in actions:
            if action not in DEFAULT_REASON_ACTION_TYPES:
                self.validation_results.append(f"Invalid action value: {action}")
        return not self.validation_results

    @property
    def _limit(self) -> str:
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
        order_fields = self.args.sort or ["updated"]
        order_clauses = []

        for sort_field in order_fields:
            direction = "ASC"
            field_name = sort_field

            if sort_field.startswith("-"):
                direction = "DESC"
                field_name = sort_field.removeprefix("-")
            if field_name in DefaultReasonResponse._fields:
                order_clauses.append(f"{field_name} {direction}")

        return "ORDER BY " + ", ".join(order_clauses)

    @property
    def _create_text_condition(self) -> str:
        if self.args.text:
            return f"dr_text ILIKE '%{self.args.text}%'"
        return ""

    @property
    def _create_source_condition(self) -> str:
        if self.args.source:
            return f"dr_source = '{self.args.source}'"
        return ""

    @property
    def _create_action_condition(self) -> str:
        if self.args.action:
            return f"dr_action IN {self.args.action}"
        return ""

    @property
    def _having_clause(self) -> str:
        if self.args.is_active is not None:
            return f"AND dr_is_active = {int(self.args.is_active)}"
        return ""

    @property
    def _where_clause(self) -> str:
        conditions = []

        if self._create_source_condition:
            conditions.append(self._create_source_condition)

        if self._create_text_condition:
            conditions.append(self._create_text_condition)

        if self._create_action_condition:
            conditions.append(self._create_action_condition)

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
                    "args": self.args._asdict(),
                }
            )

        total_count = response[0][-1]

        reasons = [
            DefaultReasonResponse(
                text=text,
                source=source,
                action=action,
                is_active=bool(is_active),
                updated=updated,
            )
            for text, source, action, is_active, _, updated, _ in response
        ]

        return (
            {
                "request_args": self.args._asdict(),
                "length": len(reasons),
                "reasons": [el._asdict() for el in reasons],
            },
            200,
            {
                "Access-Control-Expose-Headers": "X-Total-Count",
                "X-Total-Count": total_count,
            },
        )

    def metadata(self) -> WorkerResult:
        metadata = []
        for arg in default_reasons_list_args.args:
            item_info = {
                "name": arg.name,
                "label": arg.name.replace("_", " ").capitalize(),
                "help_text": arg.help,
            }

            if arg.name == "text":
                metadata.append(MetadataItem(**item_info, type=KnownFilterTypes.STRING))

            if arg.name == "source":
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

            if arg.name == "action":
                metadata.append(
                    MetadataItem(
                        **item_info,
                        type=KnownFilterTypes.MULTIPLE_CHOICE,
                        choices=[
                            MetadataChoiceItem(value=v, display_name=v.capitalize())
                            for v in DEFAULT_REASON_ACTION_TYPES
                        ],
                    )
                )

            if arg.name == "is_active":
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

        return {
            "length": len(metadata),
            "metadata": [el.asdict() for el in metadata],
        }, 200
