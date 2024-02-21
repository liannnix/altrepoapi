# ALTRepo API
# Copyright (C) 2021-2023  BaseALT Ltd

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
from altrepo_api.utils import make_tmp_table_name, get_real_ip

from .tools.base import ChangeReason, ChangeSource, PncRecord, UserInfo
from .tools.constants import (
    CHANGE_ACTION_CREATE,
    CHANGE_ACTION_DISCARD,
    CHANGE_ACTION_UPDATE,
    # CHANGE_SOURCE_KEY,
    # CHANGE_SOURCE_MANUAL,
    DRY_RUN_KEY,
    PNC_STATES,
    PNC_STATE_ACTIVE,
    PNC_STATE_INACTIVE,
    PNC_STATE_CANDIDATE,
)
from .tools.utils import validate_action
from ..sql import sql


class ManagePnc(APIWorker):
    def __init__(self, connection, payload, **kwargs):
        self.payload: dict[str, Any] = payload
        self.dry_run = kwargs.get(DRY_RUN_KEY, False)
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        # values set in self.check_params_xxx() call
        self.action: str
        self.pnc: PncRecord
        self.reason: ChangeReason
        super().__init__()

    def _valiadte_and_parse(self):
        """Validate and parse `self.payload' JSON contents."""

        self.reason = ChangeReason(
            actor=UserInfo(
                name=self.payload.get("user", ""),
                ip=get_real_ip(),
            ),
            message=self.payload.get("reason", ""),
            details={},
        )

        self.action = self.payload.get("action", "")

        if not self.reason.actor.name:
            self.validation_results.append("User name should be specified")

        if not self.reason.message:
            self.validation_results.append("PNC change reason should be specified")

        if not validate_action(self.action):
            self.validation_results.append(
                f"PNC change action '{self.action}' not supported"
            )

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        branch = self.args.get("branch", None)
        pkg_name = self.args.get("package_name", None)
        proj_name = self.args.get("project_name", None)

        if not branch and not pkg_name and not proj_name:
            self.validation_results.append(
                "At least one of 'package_name', 'project_name' or 'branch' "
                "arguments should be specified"
            )
            return False

        if branch is not None and branch not in lut.cpe_branch_map:
            self.validation_results.append(f"Invalid branch: {branch}")
            return False

        return True

    def check_params_post(self) -> bool:
        self._valiadte_and_parse()

        if self.validation_results != []:
            return False

        if not self.action == CHANGE_ACTION_CREATE:
            self.validation_results.append("Change action validation error")

        if self.pnc.pnc_state in (PNC_STATE_INACTIVE, PNC_STATE_CANDIDATE):
            self.validation_results.append(
                f"Invalid PNC record state: {self.pnc.asdict()}"
            )

        if self.validation_results != []:
            return False
        return True

    def check_params_put(self) -> bool:
        self._valiadte_and_parse()

        if self.validation_results != []:
            return False

        if not self.action == CHANGE_ACTION_UPDATE:
            self.validation_results.append("Change action validation error")

        if self.pnc.pnc_state != PNC_STATE_ACTIVE:
            self.validation_results.append(
                f"Invalid PNC record state: {self.pnc.asdict()}"
            )

        if self.validation_results != []:
            return False
        return True

    def check_params_delete(self) -> bool:
        self._valiadte_and_parse()

        if self.validation_results != []:
            return False

        if not self.action == CHANGE_ACTION_DISCARD:
            self.validation_results.append("Change action validation error")

        if self.pnc.pnc_state != PNC_STATE_INACTIVE:
            self.validation_results.append(
                f"Invalid PNC record state: {self.pnc.asdict()}"
            )

        if self.validation_results != []:
            return False
        return True

    def get(self):
        """Get PNC records, active and candidate, by package name or project name
        and branch if specified."""

        pnc_records: list[PncRecord] = []

        branch = self.args.get("branch")
        if branch:
            branch = (lut.cpe_branch_map[branch],)
        else:
            branch = tuple(lut.cpe_reverse_branch_map.keys())

        pkg_name = self.args.get("package_name")
        proj_name = self.args.get("project_name")

        state = self.args.get("state")
        if state == "all":
            state = None

        # build where clause for PNC records gathering request
        where_conditions = ["WHERE 1"]

        if branch:
            where_conditions.append(f"type IN {branch}")
        if pkg_name:
            where_conditions.append(f"name = '{pkg_name}'")
        if proj_name:
            where_conditions.append(f"result = '{proj_name}'")
        if state:
            where_conditions.append(f"state = '{state}'")

        where_clause = " AND ".join(where_conditions)

        # get PNC records from DB
        response = self.send_sql_request(
            self.sql.get_pnc_records.format(where_clause=where_clause)
        )
        if not self.sql_status:
            return self.error

        pnc_records = [PncRecord(*el) for el in response]

        if not pnc_records:
            return self.store_error(
                {"message": f"No data found in DB for {self.args}"}, http_code=404
            )

        return {
            "request_args": self.args,
            "pncs": [r.asdict() for r in pnc_records],
        }, 200

    def post(self):
        return "OK", 200

    def put(self):
        return "OK", 200

    def delete(self):
        return "OK", 200
