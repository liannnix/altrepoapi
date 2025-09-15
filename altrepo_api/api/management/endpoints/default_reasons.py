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

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Optional

from altrepo_api.api.base import APIWorker
from altrepo_api.utils import get_logger

from .tools.constants import (
    CHANGE_ACTION_CREATE,
    CHANGE_ACTION_DISCARD,
    CHANGE_ACTION_UPDATE,
)
from .tools.utils import (
    validate_action,
    validate_default_reason_source,
)
from ..sql import sql

logger = get_logger(__name__)


@dataclass
class DefaultReasonReasonPayload:
    text: str
    source: str
    is_active: bool
    updated: datetime = datetime.now()

    def validate(self) -> list[str]:
        validation_errors = []
        if not self.text:
            validation_errors.append("'text' field should be specified")

        if not validate_default_reason_source(self.source):
            validation_errors.append("Invalid 'source' field value")

        if not isinstance(self.is_active, bool):
            validation_errors.append("'is_active' field should be boolean")

        return validation_errors

    def to_sql(self) -> dict[str, Any]:
        return {
            "dr_text": self.text,
            "dr_source": self.source,
            "dr_is_active": int(self.is_active),
        }


@dataclass
class DefaultReasonPayload:
    default_reason: DefaultReasonReasonPayload
    action: str

    def validate(self) -> list[str]:
        validation_errors = []

        if not validate_action(self.action):
            validation_errors.append(
                f"Default reason change action '{self.action}' is not supported"
            )

        validation_errors.extend(self.default_reason.validate())

        return validation_errors

    def validate_with_match(
        self, match: Optional[DefaultReasonReasonPayload]
    ) -> list[str]:
        validations = []

        if self.action == CHANGE_ACTION_CREATE and match is not None:
            validations.append("This default reason exists in DB already.")

        if self.action != CHANGE_ACTION_CREATE:
            if match is None:
                validations.append("This default reason does not exist in DB.")
            elif match.is_active and self.action == CHANGE_ACTION_UPDATE:
                validations.append("This default reason is active already.")
            elif (not match.is_active) and self.action == CHANGE_ACTION_DISCARD:
                validations.append("This default reason is not active already.")

        return validations


class DefaultReasons(APIWorker):
    """
    Post, disable or enable a default reason.
    """

    def __init__(self, connection, payload: dict[str, Any], **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql

        self.payload = DefaultReasonPayload(
            default_reason=DefaultReasonReasonPayload(**payload["default_reason"]),
            action=payload["action"],
        )

        super().__init__()

    def check_payload_post(self) -> bool:
        self.validation_results = self.payload.validate()
        if self.payload.action != CHANGE_ACTION_CREATE:
            self.validation_results.append(
                f"Wrong action for this method: {self.payload.action}"
            )
        return self.validation_results == []

    def check_payload_put(self) -> bool:
        self.validation_results = self.payload.validate()
        if self.payload.action != CHANGE_ACTION_UPDATE:
            self.validation_results.append(
                f"Wrong action for this method: {self.payload.action}"
            )
        return self.validation_results == []

    def check_payload_delete(self) -> bool:
        self.validation_results = self.payload.validate()
        if self.payload.action != CHANGE_ACTION_DISCARD:
            self.validation_results.append(
                f"Wrong action for this method: {self.payload.action}"
            )
        return self.validation_results == []

    def post(self):
        return self._handle_request()

    def put(self):
        return self._handle_request()

    def delete(self):
        return self._handle_request()

    def _handle_request(self):
        # validate request payload with records from DB
        where_clause = (
            f"WHERE dr_text = '{self.payload.default_reason.text}' "
            f"AND dr_source = '{self.payload.default_reason.source}'"
        )

        response = self.send_sql_request(
            self.sql.get_default_reasons_list.format(
                where_clause=where_clause,
                having_clause="",
                order_by="",
                limit="",
                offset="",
            )
        )

        if not self.sql_status:
            return self.error

        existing_reason = (
            None if len(response) != 1 else DefaultReasonReasonPayload(*response[0][:3])
        )

        if validation_errors := self.payload.validate_with_match(existing_reason):
            return {
                "message": "Request payload validation error",
                "errors": validation_errors,
            }, 400

        # commit changes to DB
        updated_reason = self.payload.default_reason
        updated_reason.is_active = self.payload.action != CHANGE_ACTION_DISCARD

        self.send_sql_request(
            (self.sql.store_default_reason, [updated_reason.to_sql()])
        )

        if not self.sql_status:
            return self.error

        self.logger.info("All changes comitted to DB.")

        return {
            "request_args": self.args,
            "result": "OK",
            "default_reason": asdict(updated_reason),
        }, 200
