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

from altrepo_api.api.base import APIWorker
from altrepo_api.libs.errata_server import ErrataServerError, UserInfo
from altrepo_api.libs.errata_server.errata_manage_service import (
    ErrataManageService,
    Errata,
    ErrataHistory,
    serialize,
)
from altrepo_api.settings import namespace as settings
from altrepo_api.utils import get_logger, get_real_ip


from .common.constants import (
    CHANGE_ACTION_CREATE,
    CHANGE_ACTION_DISCARD,
    CHANGE_ACTION_UPDATE,
    ERRATA_PACKAGE_UPDATE_PREFIX,
    ERRATA_PACKAGE_UPDATE_SOURCES,
    ERRATA_PACKAGE_UPDATE_TYPES,
    TASK_PACKAGE_ERRATA_TYPE,
    TASK_STATE_DONE,
    DT_NEVER,
    DRY_RUN_KEY,
)
from .common.utils import dt_from_iso, validate_action, validate_branch
from ..sql import sql


logger = get_logger(__name__)


def get_errata_manage_service(
    *, dry_run: bool, access_token: str, user: UserInfo
) -> ErrataManageService:
    try:
        return ErrataManageService(
            url=settings.ERRATA_MANAGE_URL,
            access_token=access_token,
            user=user,
            dry_run=dry_run,
        )
    except ErrataServerError as e:
        logger.error(f"Failed to connect to Errata Server: {e}")
        raise RuntimeError("error: %s" % e)


def json2eh(js: dict[str, Any]) -> Errata:
    is_discarded = js.pop("is_discarded", False)
    return Errata(
        eh=ErrataHistory(
            **js,
            hash="",
            json=None,
        ),
        is_discarded=is_discarded,
    )


class ManageErrata(APIWorker):
    """Errata records management handler."""

    def __init__(self, connection, payload, **kwargs):
        self.payload: dict[str, Any] = payload
        self.dry_run = kwargs.get(DRY_RUN_KEY, True)
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        # values set in self.check_params_xxx() call
        self.user: UserInfo
        self.errata: Errata
        self.action: str
        self.reason: str
        super().__init__()

    def _valiadte_and_parse(self):
        """Validate and parse `self.payload' JSON contents."""

        self.user = UserInfo(
            name=self.payload.get("user", ""),
            ip=get_real_ip(),
        )

        self.action = self.payload.get("action", "")
        self.reason = self.payload.get("reason", "")

        if not self.user.name:
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
                self.errata = json2eh(errata)
            except Exception as e:
                self.validation_results.append(f"Failed to parse errata object: {e}")
                return

        if not self.errata.eh.references:
            self.validation_results.append(
                "Invalid errata contents: references shouldn't be empty"
            )

        if self.errata.eh.type not in ERRATA_PACKAGE_UPDATE_TYPES:
            self.validation_results.append("Incorrect errata type")

        if self.errata.eh.source not in ERRATA_PACKAGE_UPDATE_SOURCES:
            self.validation_results.append("Incorrect errata source")

        if not validate_branch(self.errata.eh.pkgset_name):
            self.validation_results.append("Incorrect branch data")

        if self.errata.eh.type == TASK_PACKAGE_ERRATA_TYPE:
            if (
                self.errata.eh.task_id <= 0
                or self.errata.eh.subtask_id <= 0
                or self.errata.eh.task_state != TASK_STATE_DONE
            ):
                self.validation_results.append("Incorrect task data")

        if (
            self.errata.eh.pkg_name == ""
            or self.errata.eh.pkg_version == ""
            or self.errata.eh.pkg_release == ""
            or int(self.errata.eh.pkg_hash) <= 0
        ):
            self.validation_results.append("Incorrect package data")

    def check_params_put(self) -> bool:
        self._valiadte_and_parse()
        if self.validation_results != []:
            return False

        # validate request payload contents for particular HTTP method
        if self.errata.eh.id is None:
            self.validation_results.append(
                "Failed to get or parse errata ID from request payload."
            )
        elif not self.errata.eh.id.startswith(ERRATA_PACKAGE_UPDATE_PREFIX):
            self.validation_results.append(
                "API requests supports only package update errata records."
            )

        if not self.action == CHANGE_ACTION_UPDATE:
            self.validation_results.append("Errata change action validation error")

        if (
            dt_from_iso(self.errata.eh.created) <= DT_NEVER
            or dt_from_iso(self.errata.eh.updated) <= DT_NEVER
        ):
            self.validation_results.append("Incorrect errata dates information")

        if self.validation_results != []:
            return False
        return True

    def check_params_post(self) -> bool:
        self._valiadte_and_parse()
        if self.validation_results != []:
            return False

        # validate request payload contents for particular HTTP method
        if not self.action == CHANGE_ACTION_CREATE:
            self.validation_results.append("Errata change action validation error")

        if self.errata.eh.id:
            self.validation_results.append("Errata ID should be empty.")

        if self.validation_results != []:
            return False
        return True

    def check_params_delete(self) -> bool:
        self._valiadte_and_parse()
        if self.validation_results != []:
            return False

        # validate request payload contents for particular HTTP method
        if not self.action == CHANGE_ACTION_DISCARD:
            self.validation_results.append("Errata change action validation error")

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
        errata_id = self.args["errata_id"]

        service = get_errata_manage_service(
            dry_run=True, access_token="", user=UserInfo("", "")
        )

        try:
            response = service.get(errata_id)
        except ErrataServerError as e:
            return self.store_error(
                {"message": f"Failed to get data from Errata Server: {e}"},
                severity=self.LL.ERROR,
                http_code=e.status_code or 500,
            )

        return {
            "request_args": self.args,
            "message": "OK",
            "errata": response.errata.asdict(),
            "vulns": [serialize(v) for v in response.vulns],
        }, 200

    def post(self):
        """Handles errata record create.
        Returns:
            - 200 (OK) if errata record created successfully
            - 400 (Bad request) on paload validation errors
            - 409 (Conflict) if such errata exists already or data is inconsistent with DB
        """

        service = get_errata_manage_service(
            dry_run=self.dry_run,
            access_token=settings.ERRATA_SERVER_TOKEN,
            user=self.user,
        )

        try:
            response = service.create(self.reason, self.errata.eh)
        except ErrataServerError as e:
            return self.store_error(
                {"message": f"Failed to create Errata: {e}"},
                severity=self.LL.ERROR,
                http_code=e.status_code or 500,
            )

        return {
            "action": self.action,
            "message": response.result,
            "errata": [e.asdict() for e in response.errata],
            "errata_change": [serialize(ec) for ec in response.errata_change],
        }, 200

    def put(self):
        """Handles errata record update.
        Returns:
            - 200 (OK) if errata record version was updated or no changes found to be made
            - 400 (Bad request) on paload validation errors
            - 404 (Not found) if errata discarded already or does not exists
            - 409 (Conflict) if errata version update failed due to outdated version
        """

        service = get_errata_manage_service(
            dry_run=self.dry_run,
            access_token=settings.ERRATA_SERVER_TOKEN,
            user=self.user,
        )

        try:
            response = service.update(self.reason, self.errata.eh)
        except ErrataServerError as e:
            return self.store_error(
                {"message": f"Failed to update Errata: {e}"},
                severity=self.LL.ERROR,
                http_code=e.status_code or 500,
            )

        return {
            "action": self.action,
            "message": response.result,
            "errata": [e.asdict() for e in response.errata],
            "errata_change": [serialize(ec) for ec in response.errata_change],
        }, 200

    def delete(self):
        """Handles errata record discard.
        Returns:
            - 200 (OK) if errata record discarded successfully
            - 400 (Bad request) on paload validation errors
            - 404 (Not found) if errata discarded already or does not exists
        """

        service = get_errata_manage_service(
            dry_run=self.dry_run,
            access_token=settings.ERRATA_SERVER_TOKEN,
            user=self.user,
        )

        try:
            response = service.discard(self.reason, self.errata.eh)
        except ErrataServerError as e:
            return self.store_error(
                {"message": f"Failed to discard Errata: {e}"},
                severity=self.LL.ERROR,
                http_code=e.status_code or 500,
            )

        return {
            "action": self.action,
            "message": response.result,
            "errata": [e.asdict() for e in response.errata],
            "errata_change": [serialize(ec) for ec in response.errata_change],
        }, 200
