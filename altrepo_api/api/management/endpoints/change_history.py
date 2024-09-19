# ALTRepo API
# Copyright (C) 2021-2024  BaseALT Ltd

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
from dataclasses import dataclass, asdict, field

from altrepo_api.api.base import APIWorker
from .tools.constants import ERRATA_PACKAGE_UPDATE_PREFIX, ERRATA_BRANCH_BULLETIN_PREFIX

from ..sql import sql


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
        eh_type_clause = ""
        ec_origin_clause = ""

        if errata_id.startswith(ERRATA_PACKAGE_UPDATE_PREFIX):
            eh_type_clause = "AND eh_type != 'bulletin'"
            ec_origin_clause = "AND ec_origin = 'parent'"
        if errata_id.startswith(ERRATA_BRANCH_BULLETIN_PREFIX):
            eh_type_clause = "AND eh_type == 'bulletin'"
            ec_origin_clause = "AND ec_origin = 'child'"

        response = self.send_sql_request(
            self.sql.get_errata_history.format(
                errata_id=errata_id, type=eh_type_clause, origin=ec_origin_clause
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
