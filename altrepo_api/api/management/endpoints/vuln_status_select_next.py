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

from .common.utils import make_date_condition
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

    def check_params(self) -> bool:
        self.logger.debug(f"args : {self.args}")
        return True

    def _date_interval_condition(self) -> str:
        start_date = self.args.get("modified_start_date")
        end_date = self.args.get("modified_end_date")

        if condition := make_date_condition(start_date, end_date):
            return f"AND vuln_modified_date {condition}"

        return ""

    def _current_vuln_condidition(self) -> str:
        current_vuln_id = self.args.get("current_vuln_id")

        if current_vuln_id:
            return f"AND vuln_id != '{current_vuln_id}'"
        return ""

    def get(self) -> WorkerResult:
        response = self.send_sql_request(
            self.sql.vuln_status_select_next.format(
                date_interval_condition=self._date_interval_condition(),
                current_vuln_id=self._current_vuln_condidition(),
            )
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error({"message": "No data not found in database"})

        return {"vuln_id": response[0][0]}, 200
