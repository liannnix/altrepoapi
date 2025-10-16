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

from typing import Any, NamedTuple, Optional

from altrepo_api.api.base import APIWorker, ConnectionProtocol, WorkerResult
from altrepo_api.api.metadata import KnownFilterTypes, MetadataChoiceItem, MetadataItem

from ..sql import sql
from ..parsers import vuln_status_list_args
from .vuln_status import VulnerabilityStatus


class VulnStatusListArgs(NamedTuple):
    input: Optional[list[str]]
    status: Optional[str]
    resolution: Optional[str]
    page: Optional[int]
    limit: Optional[int]
    sort: Optional[list[str]]


class VulnStatusList(APIWorker):
    def __init__(
        self,
        conn: ConnectionProtocol,
        **kwargs: Any,
    ) -> None:
        self.conn = conn
        self.args: VulnStatusListArgs
        self.kwargs = kwargs
        self.sql = sql
        super().__init__()

    def check_params(self) -> bool:
        self.args = VulnStatusListArgs(**self.kwargs)
        self.logger.info("GET args: %s", self.args)
        return True

    def _having_clause(self) -> str:
        conditions: list[str] = []

        if self.args.input is not None:
            for val in self.args.input:
                if not val:
                    continue

                conditions.append(f"vuln_id ILIKE '%{val}%'")
                conditions.append(f"author ILIKE '%{val}%'")
                conditions.append(f"CAST(subscribers, 'String') ILIKE '%{val}%'")
                conditions.append(f"json ILIKE '%{val}%'")

        if self.args.resolution is not None:
            conditions.append(f"resolution = '%{self.args.resolution}%'")

        if self.args.status is not None:
            conditions.append(f"status = '{self.args.status}'")

        if conditions:
            return "HAVING " + " OR ".join(conditions) + "\n"

        return ""

    def _order_by_clause(self) -> str:
        order_fields = self.args.sort or ["updated"]
        order_clauses = []

        for sort_field in order_fields:
            direction = "ASC"
            field_name = sort_field.removeprefix("vs_")

            if sort_field == "json":
                continue

            if sort_field.startswith("-"):
                field_name = sort_field.removeprefix("-")
                direction = "DESC"

            if sort_field in VulnerabilityStatus._fields:
                order_clauses.append(f"{field_name} {direction}")

        if order_clauses:
            return "ORDER BY " + ", ".join(order_clauses)

        return ""

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
            sql.vuln_status_list.format(
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
                {"message": "Not found any vulnerability status with provided criteria"}
            )

        vulns_statuses = [VulnerabilityStatus(*vs) for *vs, _ in response]

        return (
            {
                "request_args": self.args._asdict(),
                "length": len(response),
                "statuses": [vs._asdict() for vs in vulns_statuses],
            },
            200,
            {
                "Access-Control-Expose-Headers": "X-Total-Count",
                "X-Total-Count": response[0][-1],
            },
        )

    def metadata(self) -> WorkerResult:
        metadata = []
        for arg in vuln_status_list_args.args:
            item_info = {
                "name": arg.name,
                "label": arg.name.replace("_", " ").capitalize(),
                "help_text": arg.help,
            }

            if arg.name == "status":
                metadata.append(
                    MetadataItem(
                        **item_info,
                        type=KnownFilterTypes.CHOICE,
                        choices=[
                            MetadataChoiceItem(
                                value=status, display_name=status.capitalize()
                            )
                            for status in arg.choices
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

            if arg.name == "sort":
                metadata.append(
                    MetadataItem(
                        **item_info,
                        type=KnownFilterTypes.CHOICE,
                        choices=[
                            MetadataChoiceItem(
                                value=field.removeprefix("vs_"),
                                display_name=(
                                    field.replace("vuln", "vulnerability")
                                    .replace("_", " ")
                                    .removeprefix("vs_")
                                    .capitalize()
                                    .replace("id", "ID")
                                ),
                            )
                            for field in VulnerabilityStatus._fields
                            if field != "vs_json"
                        ],
                    )
                )

        return {
            "length": len(metadata),
            "metadata": [el.asdict() for el in metadata],
        }, 200
