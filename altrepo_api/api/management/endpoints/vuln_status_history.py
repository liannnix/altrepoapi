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
from typing import Any, NamedTuple

from altrepo_api.api.base import APIWorker, ConnectionProtocol, WorkerResult

from ..sql import sql


class VulnerabilityStatus(NamedTuple):
    vuln_id: str
    vs_author: str
    vs_status: str
    vs_reason: str
    vs_resolution: str
    vs_subscribers: list[str]
    vs_json: str
    vs_updated: datetime

    def asdict(self) -> dict[str, Any]:
        return {
            "vuln_id": self.vuln_id,
            "author": self.vs_author,
            "status": self.vs_status,
            "reason": self.vs_reason,
            "resolution": self.vs_resolution,
            "subscribers": self.vs_subscribers,
            "json": self.vs_json,
            "updated": self.vs_updated,
        }


class VulnStatusHistory(APIWorker):
    def __init__(
        self,
        conn: ConnectionProtocol,
        args: dict[str, Any],
    ) -> None:
        self.conn = conn
        self.args = args
        self.vuln_id: str = self.args.get("vuln_id")  # type: ignore
        self.sql = sql
        super().__init__()

    def check_params(self) -> bool:
        self.logger.debug(f"args: {self.args}")
        return True

    def get(self) -> WorkerResult:
        response = self.send_sql_request(
            self.sql.vuln_status_history.format(vuln_id=self.vuln_id)
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error({"message": "No data not found in database"})

        return {
            "vuln_id": self.vuln_id,
            "history": [
                {
                    "vuln_id": vuln_id,
                    "author": author,
                    "status": status,
                    "reason": reason,
                    "resolution": resolution,
                    "subscribers": subscribers,
                    "json": json,
                    "updated": updated,
                }
                for (
                    vuln_id,
                    author,
                    status,
                    resolution,
                    reason,
                    subscribers,
                    json,
                    updated,
                ) in response
            ],
        }, 200
