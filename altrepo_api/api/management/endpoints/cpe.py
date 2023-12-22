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

from flask import request
from typing import Any, NamedTuple

from altrepo_api.api.base import APIWorker
from altrepo_api.api.misc import lut
from altrepo_api.api.vulnerabilities.endpoints.common import CPE

from .tools.base import UserInfo
from .tools.utils import validate_action, validate_branch_with_tatsks
from ..sql import sql


class CpeRaw(NamedTuple):
    state: str
    name: str
    repology_name: str
    repology_branch: str
    cpe: str


class CPECandidates(APIWorker):
    """Retrieves CPE candidates records."""

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        return True

    def get(self):
        cpes: dict[tuple[str, str], Any] = {}

        response = self.send_sql_request(
            self.sql.get_cpes.format(
                cpe_branches=tuple(set(lut.cpe_reverse_branch_map.keys())),
                pkg_name_conversion_clause="",
                cpe_states=("candidate",),
            )
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error({"Error": "No CPE candidates found in DB"})

        for el in response:
            try:
                cpe_raw = CpeRaw(*el)

                branch = lut.cpe_reverse_branch_map[cpe_raw.repology_branch][0]
                cpe = CPE(cpe_raw.cpe)
                cpe_s = str(cpe)

                if cpe.vendor == "*" or cpe.product == "*":
                    self.logger.info(f"Skip malformed CPE candidate: {el}")
                    continue

                if (cpe_s, cpe_raw.repology_name) not in cpes:
                    cpes[(cpe_s, cpe_raw.repology_name)] = {
                        "state": cpe_raw.state,
                        "packages": [{"name": cpe_raw.name, "branch": branch}],
                    }
                else:
                    cpes[(cpe_s, cpe_raw.repology_name)]["packages"].append(
                        {"name": cpe_raw.name, "branch": branch}
                    )
            except (TypeError, ValueError):
                self.logger.info(f"Failed to parse CPE from {el}")
                continue

        res = {
            "length": len(cpes),
            "cpes": [
                {"cpe": k[0], "repology_name": k[1], **v} for k, v in cpes.items()
            ],
        }

        return res, 200


class ManageCpe(APIWorker):
    """CPE records management handler."""

    def __init__(self, connection, payload, **kwargs):
        self.payload: dict[str, Any] = payload
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def _valiadte_and_parse(self):
        """Validate and parse `self.payload' JSON contents."""

        self.user_info = UserInfo(
            ip=request.remote_addr or "",
            name=self.payload.get("user", ""),
            reason=self.payload.get("reason", ""),
        )

        self.action = self.payload.get("action", "")

        if not self.user_info.name:
            self.validation_results.append("User name should be specified")

        if not self.user_info.reason:
            self.validation_results.append("Errata change reason should be specified")

        if not validate_action(self.action):
            self.validation_results.append(
                f"Errata change action '{self.action}' not supported"
            )

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        branch = self.args.get("branch", None)
        if branch is not None and not validate_branch_with_tatsks(branch):
            self.validation_results.append(f"Invalid branch: {self.args['branch']}")
            return False

        return True

    def get(self):
        """Get CPE records, active and candidate, by package name
        and branch (optional)."""

        cpes: dict[tuple[str, str], Any] = {}

        pkg_name = self.args["name"]
        branch = self.args.get("branch")
        if branch is None:
            branch = ""
            cpe_branches = tuple(set(lut.cpe_reverse_branch_map.keys()))
        else:
            cpe_branches = (lut.cpe_branch_map[branch],)

        # get last CPE match states for specific package name
        response = self.send_sql_request(
            self.sql.get_cpes.format(
                cpe_branches=cpe_branches,
                pkg_name_conversion_clause=f"AND alt_name = '{pkg_name}'",
                cpe_states=("active", "candidate"),
            )
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {"Error": f"No CPE records found in DB for package '{pkg_name}'"}
            )

        for el in response:
            try:
                cpe_raw = CpeRaw(*el)

                _branch = lut.cpe_reverse_branch_map[cpe_raw.repology_branch][0]
                cpe = CPE(cpe_raw.cpe)
                cpe_s = str(cpe)

                if cpe.vendor == "*" or cpe.product == "*":
                    self.logger.info(f"Skip malformed CPE candidate: {el}")
                    continue

                if (cpe_s, cpe_raw.repology_name) not in cpes:
                    cpes[(cpe_s, cpe_raw.repology_name)] = {
                        "state": cpe_raw.state,
                        "packages": [{"name": cpe_raw.name, "branch": _branch}],
                    }
                else:
                    cpes[(cpe_s, cpe_raw.repology_name)]["packages"].append(
                        {"name": cpe_raw.name, "branch": _branch}
                    )
            except (TypeError, ValueError):
                self.logger.info(f"Failed to parse CPE from {el}")
                continue

        return {
            "length": len(cpes),
            "name": pkg_name,
            "branch": branch,
            "cpes": [
                {"cpe": k[0], "repology_name": k[1], **v} for k, v in cpes.items()
            ],
        }, 200

    def post(self):
        return "NotImplemented", 400

    def put(self):
        return "NotImplemented", 400

    def delete(self):
        return "NotImplemented", 400
