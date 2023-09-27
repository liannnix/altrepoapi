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

from .tools.base import (
    Errata,
    ErrataID,
    ErrataChange,
    ErrataChangeOrigin,
    ErrataChangeSource,
    ErrataChangeType,
)
from .tools.constants import (
    ERRATA_CHANGE_ACTION_CREATE,
    ERRATA_CHANGE_ACTION_DISCARD,
    ERRATA_CHANGE_ACTION_UPDATE,
    ERRATA_PACKAGE_UPDATE_PREFIX,
    ERRATA_PACKAGE_UPDATE_SOURCES,
    ERRATA_PACKAGE_UPDATE_TYPES,
    BRANCH_PACKAGE_ERRATA_TYPE,
    TASK_PACKAGE_ERRATA_TYPE,
    TASK_STATE_DONE,
    DT_NEVER,
    CHEK_ERRATA_CONTENT_ON_CREATE,
)
from .tools.errata import (
    json2errata,
    build_errata_with_id_version_updated,
    update_bulletin_by_errata_discard,
    update_bulletin_by_errata_update,
    update_bulletin_by_errata_add,
    build_stub_errata,
)
from .tools.errata_id import (
    get_errataid_service,
    update_errata_id,
    register_errata_change_id,
    register_package_update_id,
)
from .tools.helpers import (
    get_errata_contents,
    get_bulletin_by_package_update,
    get_ec_id_by_package_update,
    store_errata_history_records,
    store_errata_change_records,
    get_last_errata_id_version,
    check_errata_is_discarded,
    check_errata_contents_is_changed,
    get_errata_by_task,
    is_errata_equal,
    find_closest_branch_state,
    get_bulletin_by_branch_date,
    build_new_bulletin,
    collect_errata_vulnerabilities_info,
)
from .tools.utils import validate_action, validate_branch, validate_branch_with_tatsks
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

        if self.errata.type not in ERRATA_PACKAGE_UPDATE_TYPES:
            self.validation_results.append("Incorrect errata type")

        if self.errata.source not in ERRATA_PACKAGE_UPDATE_SOURCES:
            self.validation_results.append("Incorrect errata source")

        if not validate_branch(self.errata.pkgset_name):
            self.validation_results.append("Incorrect branch data")

        if self.errata.type == TASK_PACKAGE_ERRATA_TYPE:
            if (
                self.errata.task_id <= 0
                or self.errata.subtask_id <= 0
                or self.errata.task_state != TASK_STATE_DONE
            ):
                self.validation_results.append("Incorrect task data")

        if (
            self.errata.pkg_name == ""
            or self.errata.pkg_version == ""
            or self.errata.pkg_release == ""
            or self.errata.pkg_hash <= 0
        ):
            self.validation_results.append("Incorrect package data")

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

        if self.errata.created <= DT_NEVER or self.errata.updated <= DT_NEVER:
            self.validation_results.append("Incorrect errata dates information")

        if self.validation_results != []:
            return False
        return True

    def check_params_post(self) -> bool:
        self._valiadte_and_parse()
        if self.validation_results != []:
            return False

        # validate request payload contents for particular HTTP method
        if not self.action == ERRATA_CHANGE_ACTION_CREATE:
            self.validation_results.append("Errata change action validation error")

        if self.errata.id is not None:
            self.validation_results.append("Errata ID should be empty.")

        if self.validation_results != []:
            return False
        return True

    def check_params_delete(self) -> bool:
        self._valiadte_and_parse()
        if self.validation_results != []:
            return False

        # validate request payload contents for particular HTTP method
        if not self.action == ERRATA_CHANGE_ACTION_DISCARD:
            self.validation_results.append("Errata change action validation error")

        if self.errata.created <= DT_NEVER or self.errata.updated <= DT_NEVER:
            self.validation_results.append("Incorrect errata dates information")

        if self.validation_results != []:
            return False
        return True

    def get(self):
        """Handles errata record data gather.
        Returns:
            - 200 (OK)
            - 400 (Bad request) on arguments validation errors
            - 404 (Not found) if errata does not exists in DB
            - 409 (Conflict) if errata version is outdated
        """
        self.errata = build_stub_errata(self.args["errata_id"])
        # 1. check if current errata version is the latest one
        last_errata_id = get_last_errata_id_version(self)
        if not self.status or last_errata_id is None:
            return self.error

        # 2. check if current errat is not discarded yet
        is_discarded = check_errata_is_discarded(self)
        if not self.status or not self.sql_status:
            return self.error
        if is_discarded:
            self.errata = self.errata.update(is_discarded=True)

        # 3. get and return errata contents in the same fom as used in other HTTP methods
        get_errata_contents(self)
        if not self.status or last_errata_id is None:
            return self.error

        # 4. collect bugs and vulnerabilities contents to be mainly compatible with
        # `errata/packages_updates` API endpoint
        vulns = collect_errata_vulnerabilities_info(self)
        if not self.sql_status or not self.status:
            return self.error

        return {
            "request_args": self.args,
            "message": "OK",
            "errata": self.errata.asdict(),
            "vulns": [v._asdict() for v in vulns] if vulns else [],
        }, 200

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

        # 0. check if current errat is not discarded yet
        is_discarded = check_errata_is_discarded(self)
        if not self.status or not self.sql_status:
            return self.error
        if is_discarded:
            return self.store_error(
                {
                    "message": f"Errata {self.errata.id} is discarded already.",
                },
                http_code=404,
            )

        # 1. check if current errata version is the latest one and
        # check if errata contents have been changed in fact (ensure request is idempotent)
        is_changed = check_errata_contents_is_changed(self)
        if not self.status:
            return self.error

        if not is_changed:
            return {
                "action": self.action,
                "message": f"no changes found to be saved to DB for {self.errata.id}",
                "errata": [self.errata.asdict()],
                "errata_change": [],
            }, 200

        # 2. register new errata version for package update
        new_errata = build_errata_with_id_version_updated(self.eid_service, self.errata)
        new_errata_history_records.append(new_errata)

        # 3. find affected branch update errata
        bulletin = get_bulletin_by_package_update(self, self.errata.id.id)  # type: ignore
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
                    "errata": self.errata.asdict(),
                },
                http_code=404,
                severity=self.LL.ERROR,
            )

        # 4. register new errata version for branch update
        new_bulletin = update_bulletin_by_errata_update(
            eid_service=self.eid_service,
            bulletin=bulletin,
            errata=self.errata,
            new_errata=new_errata,
        )
        new_errata_history_records.append(new_bulletin)

        # 5. register new errata change id
        # check if errata change already registered for current package update errata
        ec_errata_id = get_ec_id_by_package_update(self, self.errata.id)  # type: ignore
        if ec_errata_id is not None:
            ec_id = update_errata_id(self.eid_service, ec_errata_id.id)
        else:
            ec_id = register_errata_change_id(self.eid_service)

        # 6. create new errata change records for package and branch update erratas
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

        # 7. store new errata and errata change records to DB
        store_errata_history_records(self, new_errata_history_records)
        if not self.sql_status:
            return self.error
        store_errata_change_records(self, new_errata_change_records)
        if not self.sql_status:
            return self.error

        # 8. build API response that includes newest versions for package update errata,
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
            - 409 (Conflict) if such errata exists already or dtat inconsistent with DB
        """

        class TaskInfo(NamedTuple):
            pkg_hash: int
            pkg_name: str
            pkg_version: str
            pkg_release: str
            pkgset_name: str
            task_id: int
            subtask_id: int
            task_state: str

        new_errata_history_records: list[Errata] = []
        new_errata_change_records: list[ErrataChange] = []

        # FIXME: how to validate taskless branch package update errata contents?
        if self.errata.type == BRANCH_PACKAGE_ERRATA_TYPE:
            return self.store_error(
                {
                    "message": f"Errata type '{self.errata.type}' creation not supported",
                    "errata": self.errata.asdict(),
                },
                http_code=400,
            )
        if not validate_branch_with_tatsks(self.errata.pkgset_name):
            return self.store_error(
                {
                    "message": f"Errata branch '{self.errata.pkgset_name}' not supported",
                    "errata": self.errata.asdict(),
                },
                http_code=400,
            )

        task_info_errata = TaskInfo(
            self.errata.pkg_hash,
            self.errata.pkg_name,
            self.errata.pkg_version,
            self.errata.pkg_release,
            self.errata.pkgset_name,
            self.errata.task_id,
            self.errata.subtask_id,
            self.errata.task_state,
        )

        # 1. get task information from database
        response = self.send_sql_request(
            self.sql.get_package_info_by_task_and_subtask.format(
                task_id=self.errata.task_id, subtask_id=self.errata.subtask_id
            )
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {
                    "message": "No data foind in DB for given task and subtask",
                    "errata": self.errata.asdict(),
                }
            )
        task_info_db, task_changed = TaskInfo(*response[0][:-1]), response[0][-1]

        # 2. compare task, subtask and package data with actual DB state
        if task_info_db != task_info_errata:
            return self.store_error(
                {
                    "message": "Task package data is inconsistent with DB",
                    "errata": self.errata.asdict(),
                },
                http_code=409,
            )

        # 3. check if there is no existing or discarded errata
        errata_exists = get_errata_by_task(self)
        if not self.sql_status:
            return self.error
        if errata_exists is not None:
            is_equal = is_errata_equal(
                self.errata, errata_exists, CHEK_ERRATA_CONTENT_ON_CREATE
            )
            if is_equal and not errata_exists.is_discarded:
                return self.store_error(
                    {
                        "message": "Errata for given package is already exists in DB",
                        "errata": errata_exists.asdict(),
                    },
                    http_code=409,
                )
            elif is_equal and errata_exists.is_discarded:
                return self.store_error(
                    {
                        "message": "Errata for given package is exists in DB but was discarded already",
                        "errata": errata_exists.asdict(),
                    },
                    http_code=409,
                )
            else:
                return self.store_error(
                    {
                        "message": "Errata for given task exists in DB but package info doesn't match",
                        "errata": errata_exists.asdict(),
                    },
                    http_code=409,
                    severity=self.LL.ERROR,
                )

        # 4. find proper branch update errata to be updated
        branch_state = find_closest_branch_state(self, task_changed)
        if not self.sql_status or not self.status or branch_state is None:
            return self.error

        # 5.create and register new package update errata
        eid = register_package_update_id(self.eid_service, task_changed.year)
        self.errata = self.errata.update(
            id=eid.id, created=eid.created, updated=eid.updated
        )
        new_errata_history_records.append(self.errata)

        # 6. update and register updated branch update errata record
        new_bulletin = None
        bulletin = get_bulletin_by_branch_date(self, branch_state)
        if not self.sql_status:
            return self.error

        if bulletin is not None:
            # FIXME: handle discarded bulletin somehow
            if bulletin.is_discarded:
                return self.store_error(
                    {
                        "message": f"Can't update discarded bulletin record {bulletin.id}"
                    },
                    http_code=409,
                )
            # update existing bulletin
            bulletin = update_bulletin_by_errata_add(
                eid_service=self.eid_service, bulletin=bulletin, new_errata=self.errata
            )
            new_errata_history_records.append(bulletin)
        else:
            # create new bulletin
            new_bulletin = build_new_bulletin(self, branch_state)
            new_errata_history_records.append(new_bulletin)

        # 7. build errata change history records
        ec_id = register_errata_change_id(self.eid_service)
        new_errata_change_records = [
            ErrataChange(
                id=ErrataID.from_id(ec_id.id),
                created=ec_id.created,
                updated=ec_id.updated,
                user=self.user,
                user_ip=self.user_ip,
                reason=self.reason,
                type=ErrataChangeType.CREATE,
                source=ErrataChangeSource.MANUAL,
                origin=ErrataChangeOrigin.PARENT,
                errata_id=self.errata.id,  # type: ignore
            )
        ]

        if new_bulletin is not None:
            # new bulletin errata was created
            new_errata_change_records.append(
                ErrataChange(
                    id=ErrataID.from_id(ec_id.id),
                    created=ec_id.created,
                    updated=ec_id.updated,
                    user=self.user,
                    user_ip=self.user_ip,
                    reason=self.reason,
                    type=ErrataChangeType.CREATE,
                    source=ErrataChangeSource.AUTO,
                    origin=ErrataChangeOrigin.CHILD,
                    errata_id=new_bulletin.id,  # type: ignore
                )
            )
        else:
            # bulletin errata was updated
            new_errata_change_records.append(
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
                    errata_id=bulletin.id,  # type: ignore
                )
            )

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

    def delete(self):
        """Handles errata record discard.
        Returns:
            - 200 (OK) if errata record discarded successfully
            - 400 (Bad request) on paload validation errors
            - 404 (Not found) if errata discarded already or does not exists
        """

        new_errata_history_records: list[Errata] = []
        new_errata_change_records: list[ErrataChange] = []

        # 1. check if current errata version is the latest one
        last_errata_id = get_last_errata_id_version(self)
        if not self.status or last_errata_id is None:
            return self.error

        # 2. check if current errat is not discarded yet
        is_discarded = check_errata_is_discarded(self)
        if not self.status or not self.sql_status:
            return self.error
        if is_discarded:
            return self.store_error(
                {
                    "message": f"Errata {self.errata.id} is discarded already.",
                },
                http_code=404,
            )

        # set `is_discarded` flag and add to request results
        self.errata = self.errata.update(is_discarded=True)
        new_errata_history_records.append(self.errata)

        # 3. find affected branch update errata
        bulletin = get_bulletin_by_package_update(self, self.errata.id.id)  # type: ignore
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
                    "errata": self.errata.asdict(),
                },
                http_code=404,
                severity=self.LL.ERROR,
            )

        # 4. update branch update errata by discarded errata
        new_bulletin = update_bulletin_by_errata_discard(
            eid_service=self.eid_service, bulletin=bulletin, errata=self.errata
        )
        if new_bulletin is not None:
            new_errata_history_records.append(new_bulletin)
        else:
            self.logger.info(
                f"Discard bulletin {bulletin.id} due to {self.errata.id} was discarded"
            )
            bulletin = bulletin.update(is_discarded=True)
            new_errata_history_records.append(bulletin)

        #  5. register new errata change id
        # check if errata change already registered for current package update errata
        ec_errata_id = get_ec_id_by_package_update(self, self.errata.id)  # type: ignore
        if ec_errata_id is not None:
            ec_id = update_errata_id(self.eid_service, ec_errata_id.id)
        else:
            ec_id = register_errata_change_id(self.eid_service)

        # 6. create new errata change records for package and branch update erratas
        new_errata_change_records = [
            ErrataChange(
                id=ErrataID.from_id(ec_id.id),
                created=ec_id.created,
                updated=ec_id.updated,
                user=self.user,
                user_ip=self.user_ip,
                reason=self.reason,
                type=ErrataChangeType.DISCARD,
                source=ErrataChangeSource.MANUAL,
                origin=ErrataChangeOrigin.PARENT,
                errata_id=self.errata.id,  # type: ignore
            )
        ]

        if new_bulletin is None:
            # discrad branch update errata too if it become empty one
            new_errata_change_records.append(
                ErrataChange(
                    id=ErrataID.from_id(ec_id.id),
                    created=ec_id.created,
                    updated=ec_id.updated,
                    user=self.user,
                    user_ip=self.user_ip,
                    reason=self.reason,
                    type=ErrataChangeType.DISCARD,
                    source=ErrataChangeSource.AUTO,
                    origin=ErrataChangeOrigin.CHILD,
                    errata_id=bulletin.id,  # type: ignore
                )
            )
        else:
            # store branch update errata chnaged due to package update discard
            new_errata_change_records.append(
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
                )
            )

        # 7. store new errata and errata change records to DB
        store_errata_history_records(self, new_errata_history_records)
        if not self.sql_status:
            return self.error
        store_errata_change_records(self, new_errata_change_records)
        if not self.sql_status:
            return self.error

        # 8. build API response
        return {
            "action": self.action,
            "message": "OK",
            "errata": [e.asdict() for e in new_errata_history_records],
            "errata_change": [e.asdict() for e in new_errata_change_records],
        }, 200
