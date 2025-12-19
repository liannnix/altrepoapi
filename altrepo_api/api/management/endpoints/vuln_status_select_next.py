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

from typing import Any

from altrepo_api.api.base import APIWorker, ConnectionProtocol, WorkerResult

from ..sql import sql


class VulnStatusSelectNext(APIWorker):
    def __init__(
        self,
        conn: ConnectionProtocol,
        args: dict[str, Any],
    ) -> None:
        self.conn = conn
        self.args = args
        self.sql = sql
        super().__init__()

    def check_params_get(self) -> bool:
        self.logger.info("GET args: %s", self.args)
        return True

    def _date_interval_condition(self) -> str:
        conditions: list[str] = []

        if start_date := self.args.get("modified_start_date"):
            conditions.append(f"(vuln_modified_date >= '{start_date}')")

        if end_date := self.args.get("modified_end_date"):
            conditions.append(f"(vuln_modified_date <= '{end_date}')")

        return ("AND " + " AND ".join(conditions)) if conditions else ""

    def get(self) -> WorkerResult:
        response = self.send_sql_request(
            self.sql.vuln_status_select_next.format(
                date_interval_condition=self._date_interval_condition()
            )
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error({"message": "No data not found in database"})

        return {"vuln_id": response[0][0]}, 200
