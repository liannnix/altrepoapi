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

from altrepo_api.api.base import APIWorker, ConnectionProtocol, WorkerResult
from altrepo_api.api.metadata import KnownFilterTypes, MetadataChoiceItem, MetadataItem
from altrepo_api.api.parser import packager_nick_type
from altrepo_api.utils import make_date_condition

from ..parsers import errata_user_tracking_args
from ..sql import sql


TRACKING_ORDERING_KEYS = ("type", "id", "action", "date")


class ErrataUserTrackingArgs(NamedTuple):
    name: str
    manual_errata_changes: bool
    input: Optional[list[str]]
    type: Optional[str]
    action: Optional[str]
    subscribed_start_date: Optional[datetime]
    subscribed_end_date: Optional[datetime]
    page: Optional[int]
    limit: Optional[int]
    sort: Optional[list[str]]


class ErrataUserTracking(APIWorker):
    def __init__(self, conn: ConnectionProtocol, **kwargs) -> None:
        self.conn = conn
        self.args: ErrataUserTrackingArgs
        self.kwargs = kwargs
        self.sql = sql
        super().__init__()

    def check_params(self) -> bool:
        self.args = ErrataUserTrackingArgs(**self.kwargs)
        self.logger.debug("args: %s", self.args)

        try:
            packager_nick_type(self.args.name)
        except ValueError:
            self.validation_results.append(f"Invalid nickname: {self.args.name}")

        return self.validation_results == []

    def _only_manual_ec_clause(self) -> str:
        if self.args.manual_errata_changes:
            return "AND (ec_source = 'manual') AND (ec_origin = 'parent')"
        return ""

    def _having_clause(self) -> str:
        conditions: list[str] = []

        if self.args.input is not None:
            for val in self.args.input:
                if not val:
                    continue

                conditions.append(f"id ILIKE '%{val}%'")
                conditions.append(f"attr_link ILIKE '%{val}%'")
                conditions.append(f"text ILIKE '%{val}%'")

        if self.args.type is not None:
            conditions.append(f"type = '{self.args.type}'")

        if self.args.action is not None:
            conditions.append(f"action = '{self.args.action}'")

        if self.args.subscribed_start_date or self.args.subscribed_end_date:
            conditions.append(
                f"date {make_date_condition(self.args.subscribed_start_date, self.args.subscribed_end_date)}"
            )

        return "HAVING " + " OR ".join(conditions) if conditions else ""

    def _order_by_clause(self) -> str:
        order_fields = self.args.sort or ["-date"]
        order_clauses = []

        for sort_field in order_fields:
            direction = "ASC"
            field_name = sort_field

            if sort_field.startswith("-"):
                field_name = sort_field.removeprefix("-")
                direction = "DESC"

            if field_name in TRACKING_ORDERING_KEYS:
                order_clauses.append(f"{field_name} {direction}")

        return "ORDER BY " + ", ".join(order_clauses) if order_clauses else ""

    def _limit_clause(self) -> str:
        return f"LIMIT {self.args.limit}" if self.args.limit else ""

    def _page_clause(self) -> str:
        if self.args.limit and self.args.page:
            page = self.args.page
            per_page = self.args.limit
            offset = (page - 1) * per_page
            return f"OFFSET {offset}"
        return ""

    def get(self) -> WorkerResult:
        response = self.send_sql_request(
            self.sql.get_errata_user.format(user=self.args.name)
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error({"message": "No errata user found in database"})

        user = {
            "user": response[0][0],
            "group": response[0][1],
            "roles": response[0][2],
            "aliases": response[0][3],
        }

        response = self.send_sql_request(
            sql.get_errata_user_tracked_entities.format(
                user=user["user"],
                only_manual_ec_clause=self._only_manual_ec_clause(),
                having_clause=self._having_clause(),
                order_by_clause=self._order_by_clause(),
                limit_clause=self._limit_clause(),
                page_clause=self._page_clause(),
            )
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {"message": "Not found any tracked entity with provided criteria"}
            )

        return (
            {
                "request_args": self.args._asdict(),
                "length": len(response),
                "user": user,
                "tracks": [
                    {
                        "type": type,
                        "id": id,
                        "action": action,
                        "attr_type": attr_type,
                        "attr_link": attr_link,
                        "text": text,
                        "date": date,
                    }
                    for (
                        type,
                        id,
                        action,
                        attr_type,
                        attr_link,
                        text,
                        date,
                        _,
                    ) in response
                ],
            },
            200,
            {
                "Access-Control-Expose-Headers": "X-Total-Count",
                "X-Total-Count": response[0][-1],
            },
        )

    def metadata(self) -> WorkerResult:
        metadata = []
        for arg in errata_user_tracking_args.args:
            item_info = {
                "name": arg.name,
                "label": arg.name.replace("_", " ").capitalize(),
                "help_text": arg.help,
            }

            if arg.name == "manual_errata_changes":
                metadata.append(
                    MetadataItem(**item_info, type=KnownFilterTypes.BOOLEAN)
                )

            if arg.name == "type":
                metadata.append(
                    MetadataItem(
                        **item_info,
                        type=KnownFilterTypes.CHOICE,
                        choices=[
                            MetadataChoiceItem(
                                value=status,
                                display_name=status.replace(
                                    "vuln", "vulnerability"
                                ).capitalize(),
                            )
                            for status in arg.choices
                        ],
                    )
                )

            if arg.name == "action":
                metadata.append(
                    MetadataItem(
                        **item_info,
                        type=KnownFilterTypes.CHOICE,
                        choices=[
                            MetadataChoiceItem(
                                value=status,
                                display_name=status.capitalize(),
                            )
                            for status in arg.choices
                        ],
                    )
                )

            if arg.type.__name__ == "date_string_type":
                metadata.append(MetadataItem(**item_info, type=KnownFilterTypes.DATE))

        return {
            "length": len(metadata),
            "metadata": [el.asdict() for el in metadata],
        }, 200
