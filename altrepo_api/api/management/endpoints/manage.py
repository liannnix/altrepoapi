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
from typing import Any

from altrepo_api.api.base import APIWorker

from .tools.base import (
    Errata,
    ErrataID,
    ErrataChange,
    ErrataChangeOrigin,
    ErrataChangeSource,
    ErrataChangeType,
    Reference,
)
from .tools.constants import (
    ERRATA_CHANGE_ACTION_CREATE,
    ERRATA_CHANGE_ACTION_DISCARD,
    ERRATA_CHANGE_ACTION_UPDATE,
    ERRATA_PACKAGE_UPDATE_PREFIX,
    ERRATA_PACKAGE_UPDATE_SOURCES,
    ERRATA_PACKAGE_UPDATE_TYPES,
    TASK_PACKAGE_ERRATA_TYPE,
    TASK_STATE_DONE,
    DT_NEVER,
)
from .tools.errata import (
    json2errata,
    build_errata_with_updated_id,
    build_new_bulletin_errata,
)
from .tools.errata_id import (
    get_errataid_service,
    check_errata_id,
    update_errata_id,
    register_errata_change_id,
)
from .tools.helpers import (
    get_bulletin_by_package_update,
    get_ec_id_by_package_update,
    store_errata_history_records,
    store_errata_change_records,
)
from .tools.utils import validate_action, validate_source, validate_type

from ..sql import sql


class ManageErrata(APIWorker):
    """Errata records management handler."""

    def __init__(self, connection, payload, **kwargs):
        self.payload: dict[str, Any] = payload
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        self.eid_service = get_errataid_service()
        # values set in self.check_params_xxx() call
        self.user: str
        self.user_ip: str
        self.action: str
        self.reason: str
        self.errata: Errata
        super().__init__()

    def _valiadte_and_parse(self):
        """Validate and parse `self.payload' JSON contents."""

        user_ip = request.remote_addr
        self.user_ip = user_ip if user_ip is not None else ""

        self.user = self.payload.get("user", "")
        self.action = self.payload.get("action", "")
        self.reason = self.payload.get("reason", "")

        if not self.user:
            self.validation_results.append("User name should be specified")

        if not self.reason:
            self.validation_results.append("Errata change reason should be specified")

        if not validate_action(self.action):
            self.validation_results.append(
                f"Errata change action '{self.action}' not supported"
            )

        errata = self.payload.get("errata")
        if errata is None:
            self.validation_results.append("No errata object found")
            return
        else:
            try:
                self.errata = json2errata(errata)
            except Exception as e:
                self.validation_results.append(f"Failed to parse errata object: {e}")
                return

        if not self.errata.references:
            self.validation_results.append(
                "Invalid errata contents: references shouldn't be empty"
            )

        if not validate_type(self.errata.type):
            self.validation_results.append(f"Invalid errata type: {self.errata.type}")

        if not validate_source(self.errata.source):
            self.validation_results.append(
                f"Invalid errata source: {self.errata.source}"
            )

    def check_params(self) -> bool:
        return True

    def check_params_put(self) -> bool:
        self._valiadte_and_parse()
        if self.validation_results != []:
            return False

        # validate request payload contents for particular HTTP method
        if self.errata.id is None:
            self.validation_results.append(
                "Failed to get or parse errata ID from request payload."
            )
        elif not self.errata.id.id.startswith(ERRATA_PACKAGE_UPDATE_PREFIX):
            self.validation_results.append(
                "API requests supports only package update errata records."
            )

        if not self.action == ERRATA_CHANGE_ACTION_UPDATE:
            self.validation_results.append("Errata change action validation error")

        if self.errata.type not in ERRATA_PACKAGE_UPDATE_TYPES:
            self.validation_results.append("Incorrect errata type")

        if self.errata.source not in ERRATA_PACKAGE_UPDATE_SOURCES:
            self.validation_results.append("Incorrect errata source")

        if self.errata.type == TASK_PACKAGE_ERRATA_TYPE:
            if (
                self.errata.task_id <= 0
                or self.errata.subtask_id <= 0
                or self.errata.task_state != TASK_STATE_DONE
            ):
                self.validation_results.append("Incorrect task information")

        if (
            self.errata.pkg_name == ""
            or self.errata.pkg_version == ""
            or self.errata.pkg_release == ""
            or self.errata.pkg_hash <= 0
        ):
            self.validation_results.append("Incorrect package information")

        if self.errata.created <= DT_NEVER or self.errata.updated <= DT_NEVER:
            self.validation_results.append("Incorrect errata dates information")

        if self.validation_results != []:
            return False
        return True

    def check_params_post(self) -> bool:
        self._valiadte_and_parse()
        if self.validation_results != []:
            return False

        if not self.action == ERRATA_CHANGE_ACTION_CREATE:
            self.validation_results.append("Errata change action validation error")

        if self.validation_results != []:
            return False
        return True

    def check_params_delete(self) -> bool:
        self._valiadte_and_parse()
        if self.validation_results != []:
            return False

        if not self.action == ERRATA_CHANGE_ACTION_DISCARD:
            self.validation_results.append("Errata change action validation error")

        if self.validation_results != []:
            return False
        return True

    def get(self):
        return "OK", 200

    def put(self):
        """Handles errata record update.
        Returns:
            - 200 (OK) if errata record version updated or no changes found to be made
            - 400 (Bad request) on paload validation errors
            - 404 (Not found) if errata discarded already or does not exists
            - 409 (Conflict) if errata version update failed due to outdated version
        """

        new_errata_history_records: list[Errata] = []
        new_errata_change_records: list[ErrataChange] = []

        # XXX: get rid of type check errors here due to
        # self.errata.id is set properly during request payload validation
        if self.errata.id is None:
            return "fail", 400

        # 1. check if current errata version is the latest one
        last_errata_id = check_errata_id(self.eid_service, self.errata.id)
        if self.errata.id < last_errata_id:
            return self.store_error(
                {
                    "message": f"Errata ID version is outdated: {self.errata.id} < {last_errata_id}"
                },
                http_code=409,
            )
        elif self.errata.id > last_errata_id:
            return self.store_error(
                {
                    "message": (
                        f"Errata ID version not found in DB: {self.errata.id}. "
                        f"Lates found version is {last_errata_id}"
                    )
                },
                http_code=404,
            )

        # 2. check if errata contents have been changed in fact (ensure request is idempotent)
        response = self.send_sql_request(
            self.sql.get_errata_info.format(errata_id=last_errata_id.id)
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {"message": f"Failed to get errata info from DB for {last_errata_id}"}
            )
        r = response[0]
        errata_from_db = Errata(
            ErrataID.from_id(r[0]), *r[1:-2], [Reference(*el) for el in r[-2]], r[-1]  # type: ignore
        )

        if self.errata.hash == errata_from_db.hash:
            return {
                "action": self.action,
                "message": f"no changes found to be saved to DB for {self.errata.id}",
                "errata": [self.errata.asdict()],
            }, 200

        # 3. register new errata version for package update
        new_errata = build_errata_with_updated_id(self.eid_service, self.errata)
        new_errata_history_records.append(new_errata)

        # 4. find affected branch update errata
        bulletin = get_bulletin_by_package_update(self, self.errata.id.id)
        if not self.sql_status:
            return self.error

        if bulletin is None:
            # XXX: shouldn't ever happen
            return self.store_error(
                {
                    "message": (
                        f"Failed to find branch update errata for {self.errata.id}. "
                        "This shouldn't happen and means possible DB inconsistency."
                    ),
                    "errata": [self.errata.asdict()],
                },
                http_code=404,
            )

        # 5. register new errata version for branch update
        new_bulletin = build_new_bulletin_errata(
            self.eid_service, bulletin, self.errata, new_errata
        )
        new_errata_history_records.append(new_bulletin)

        # 6. register new errata change id
        # check if errata change already registered for current package update errata
        ec_errata_id = get_ec_id_by_package_update(self, self.errata.id)
        if ec_errata_id is not None:
            ec_id = update_errata_id(self.eid_service, ec_errata_id.id)
        else:
            ec_id = register_errata_change_id(self.eid_service)

        # 7. create new erracha change records for package and branch update erratas
        new_errata_change_records = [
            ErrataChange(
                id=ErrataID.from_id(ec_id.id),
                created=ec_id.created,
                updated=ec_id.updated,
                user=self.user,
                user_ip=self.user_ip,
                reason=self.reason,
                type=ErrataChangeType.UPDATE,
                source=ErrataChangeSource.MANUAL,
                origin=ErrataChangeOrigin.PARENT,
                errata_id=new_errata.id,  # type: ignore
            ),
            ErrataChange(
                id=ErrataID.from_id(ec_id.id),
                created=ec_id.created,
                updated=ec_id.updated,
                user=self.user,
                user_ip=self.user_ip,
                reason=self.reason,
                type=ErrataChangeType.UPDATE,
                source=ErrataChangeSource.AUTO,
                origin=ErrataChangeOrigin.CHILD,
                errata_id=new_bulletin.id,  # type: ignore
            ),
        ]

        # 8. store new errata and errata change records to DB
        store_errata_history_records(self, new_errata_history_records)
        if not self.sql_status:
            return self.error
        store_errata_change_records(self, new_errata_change_records)
        if not self.sql_status:
            return self.error

        # 9. build API response that includes newest versions for package update errata,
        # branch update errata and errata change records
        return {
            "action": self.action,
            "message": "OK",
            "errata": [e.asdict() for e in new_errata_history_records],
            "errata_change": [e.asdict() for e in new_errata_change_records],
        }, 200

    def post(self):
        """Handles errata record cretate.
        Returns:
            - 200 (OK) if errata record created successfully
            - 400 (Bad request) on paload validation errors
            - 409 (Conflict) if such errata exists already
        """

        return "OK", 200

    def delete(self):
        """Handles errata record discard.
        Returns:
            - 200 (OK) if errata record discarded successfully
            - 400 (Bad request) on paload validation errors
            - 404 (Not found) if errata discarded already or does not exists
        """

        return "OK", 200
