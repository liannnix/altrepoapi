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

from typing import Any, NamedTuple, Union

from altrepo_api.api.base import APIWorker
from altrepo_api.api.misc import lut

from ..sql import sql


class AVScanIssuesArgs(NamedTuple):
    scanner: Union[str, None]
    type: Union[str, None]


class AVScanListIssues(NamedTuple):
    av_scanner: str
    av_issue: str
    av_type: str

    def asdict(self) -> dict[str, Any]:
        return {
            "av_scanner": self.av_scanner,
            "av_issue": self.av_issue,
            "av_type": self.av_type,
        }


class AntivirusScanIssueList(APIWorker):
    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args: AVScanIssuesArgs = AVScanIssuesArgs(**kwargs)
        self.sql = sql
        super().__init__()

    @property
    def _where_clause(self) -> str:
        """
        Search conditions for antivirus issues.
        """
        where_clause = (
            f" AND av_scanner = '{self.args.scanner}'"
            if self.args.scanner and self.args.scanner != "all"
            else ""
        )
        where_clause += (
            (
                (
                    f" AND av_type = '{self.args.type}'"
                    if where_clause
                    else f"AND av_type = '{self.args.type}'"
                )
                if self.args.type and self.args.type != "all"
                else ""
            )
            if self.args.type and self.args.type != "all"
            else ""
        )

        return where_clause

    def get(self):
        response = self.send_sql_request(
            self.sql.get_all_av_issues.format(where_clause=self._where_clause)
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {"message": "No data not found in database"},
            )

        issues = [AVScanListIssues(*r).asdict() for r in response]

        res = {
            "length": len(issues),
            "issues": issues,
        }
        return (
            res,
            200,
            {
                "Access-Control-Expose-Headers": "X-Total-Count",
                "X-Total-Count": len(issues),
            },
        )


class AntivirusScanBranchesList(APIWorker):
    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args: AVScanIssuesArgs = AVScanIssuesArgs(**kwargs)
        self.sql = sql
        super().__init__()

    def get(self):
        av_branches = [b for b in lut.av_supported_branches]
        return {"length": len(av_branches), "branches": av_branches}, 200
