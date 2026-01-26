# ALTRepo API
# Copyright (C) 2024 BaseALT Ltd

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
from altrepo_api.utils import sort_branches

from ..sql import sql
from ..parsers import av_results_args


class AVScanArgs(NamedTuple):
    input: Optional[str]
    limit: Optional[int]
    page: Optional[int]
    sort: Optional[list[str]]
    branch: Optional[str]
    scanner: Optional[str]
    issue: Optional[str]
    target: Optional[str]


class DetectInfo(NamedTuple):
    av_scanner: str
    av_type: str
    av_issue: str
    av_message: str
    av_target: str
    av_date: datetime


class AVScanListResponse(NamedTuple):
    pkgset_name: str
    pkg_name: str
    pkg_version: str
    pkg_release: str
    pkg_hash: str
    file_name: str
    detect_info: list[DetectInfo]

    def asdict(self) -> dict[str, Any]:
        return {
            "pkgset_name": self.pkgset_name,
            "pkg_name": self.pkg_name,
            "pkg_version": self.pkg_version,
            "pkg_release": self.pkg_release,
            "pkg_hash": self.pkg_hash,
            "file_name": self.file_name,
            "detect_info": [el._asdict() for el in self.detect_info],
        }


class AntivirusScanResults(APIWorker):
    """
    Get a list of all Antivirus detected errors from the database.
    """

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.kwargs = kwargs
        self.args: AVScanArgs
        self.sql = sql
        super().__init__()

    def check_params(self):
        self.logger.debug(f"args : {self.kwargs}")
        self.args = AVScanArgs(**self.kwargs)
        return True

    @property
    def _limit_clause(self) -> str:
        if self.args.limit:
            return f"LIMIT {self.args.limit}"
        return ""

    @property
    def _page_clause(self) -> str:
        if self.args.page:
            return f"OFFSET {self.args.page}"
        return ""

    @property
    def _order_by_clause(self) -> str:
        order_fields = self.args.sort or []
        order_clauses = []

        for sort_field in order_fields:
            direction = "ASC"
            field_name = sort_field

            if sort_field.startswith("-"):
                direction = "DESC"
                field_name = sort_field.removeprefix("-")
            if field_name in AVScanListResponse._fields:
                order_clauses.append(f"{field_name} {direction}")

        if order_clauses:
            return "ORDER BY " + ", ".join(order_clauses)
        return ""

    @property
    def _where_clause(self) -> str:
        conditions = []

        if self.args.branch and self.args.branch != "all":
            conditions.append(f"pkgset_name = '{self.args.branch}'")
        if self.args.scanner and self.args.scanner != "all":
            conditions.append(f"av_scanner = '{self.args.scanner}'")
        if self.args.issue:
            conditions.append("av_issue = %(issue)s")
        if self.args.target and self.args.target != "all":
            conditions.append(f"av_target IN ('{self.args.target}')")
        if self.args.input:
            conditions.append(
                "(pkg_name ILIKE %(input_match)s OR av_message ILIKE %(input_match)s)"
            )

        if conditions:
            return "AND " + " AND ".join(conditions)

        return "AND av_target in ('images', 'branch')"

    def _sql_params(self) -> dict[str, object]:
        params: dict[str, object] = {}
        if self.args.issue:
            params["issue"] = self.args.issue
        if self.args.input:
            params["input_match"] = f"%{self.args.input}%"
        return params

    def get(self):
        response = self.send_sql_request(
            (
                self.sql.src_av_detections.format(
                    where_clause=self._where_clause,
                    order_by_clause=self._order_by_clause,
                    limit_clause=self._limit_clause,
                    page_clause=self._page_clause,
                ),
                self._sql_params(),
            )
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {"message": "No data not found in database"},
            )

        res = [
            AVScanListResponse(
                pkgset_name=pkgset_name,
                pkg_name=pkg_name,
                pkg_version=pkg_version,
                pkg_release=pkg_release,
                pkg_hash=pkg_hash,
                file_name=file_name,
                detect_info=[DetectInfo(*r) for r in reports],
            ).asdict()
            for pkgset_name, pkg_hash, pkg_name, pkg_version, pkg_release, file_name, reports, _ in response
        ]

        return (
            {
                "length": len(res),
                "detections": res,
            },
            200,
            {
                "Access-Control-Expose-Headers": "X-Total-Count",
                "X-Total-Count": int(response[0][-1]),
            },
        )

    def metadata(self) -> WorkerResult:
        metadata = []
        for arg in av_results_args.args:
            item_info = {
                "name": arg.name,
                "label": arg.name.replace("_", " ").capitalize(),
                "help_text": arg.help,
            }

            if arg.name == "branch":
                metadata.append(
                    MetadataItem(
                        **item_info,
                        type=KnownFilterTypes.CHOICE,
                        choices=[MetadataChoiceItem(value="all", display_name="all")]
                        + [
                            MetadataChoiceItem(value=choice, display_name=choice)
                            for choice in sort_branches(
                                list(filter(lambda b: b != "all", arg.choices))
                            )
                        ],
                    )
                )

            if arg.name in ("scanner", "target"):
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

            if arg.name == "issue":
                response = self.send_sql_request(
                    self.sql.get_all_av_issues.format(where_clause="")
                )
                if response:
                    metadata.append(
                        MetadataItem(
                            **item_info,
                            type=KnownFilterTypes.CHOICE,
                            choices=[
                                MetadataChoiceItem(
                                    value=av_issue,
                                    display_name=av_issue,
                                )
                                for av_scanner, av_issue, _ in response
                            ],
                        )
                    )

        return {
            "length": len(metadata),
            "metadata": [el.asdict() for el in metadata],
        }, 200
