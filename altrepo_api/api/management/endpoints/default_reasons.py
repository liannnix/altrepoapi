# ALTRepo API
# Copyright (C) 2021-2026  BaseALT Ltd

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

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Optional

from altrepo_api.api.base import APIWorker
from altrepo_api.utils import get_logger

from .common.constants import (
    CHANGE_ACTION_CREATE,
    CHANGE_ACTION_DISCARD,
    CHANGE_ACTION_UPDATE,
)
from .common.utils import (
    validate_action,
    validate_default_reason_action,
    validate_default_reason_source,
)
from ..sql import sql

logger = get_logger(__name__)


@dataclass
class DefaultReasonRecord:
    text: str
    source: str
    action: str
    is_active: bool
    is_deleted: bool = False
    updated: datetime = field(init=False)

    def validate(self) -> list[str]:
        validation_errors = []
        if not self.text:
            validation_errors.append("'text' field should be specified")

        if not validate_default_reason_source(self.source):
            validation_errors.append("Invalid 'source' field value")

        if not validate_default_reason_action(self.action):
            validation_errors.append("Invalid 'action' field value")

        if not isinstance(self.is_active, bool):
            validation_errors.append("'is_active' field should be boolean")

        return validation_errors

    def to_sql(self) -> dict[str, Any]:
        return {
            "dr_text": self.text,
            "dr_source": self.source,
            "dr_action": self.action,
            "dr_is_active": int(self.is_active),
            "dr_is_deleted": int(self.is_deleted),
        }


@dataclass
class DefaultReasonPayload:
    default_reason: DefaultReasonRecord
    default_reason_prev: Optional[DefaultReasonRecord]
    action: str

    def validate(self) -> list[str]:
        validation_errors = []

        if not validate_action(self.action):
            validation_errors.append(
                f"Default reason change action '{self.action}' is not supported"
            )

        validation_errors.extend(self.default_reason.validate())
        if self.default_reason_prev is not None:
            validation_errors.extend(self.default_reason_prev.validate())

        return validation_errors


class DefaultReasons(APIWorker):
    """
    Post, disable or enable a default reason.
    """

    def __init__(self, connection, payload: dict[str, Any], **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql

        default_reason_prev = None
        if dr_prev := payload.get("default_reason_prev"):
            default_reason_prev = DefaultReasonRecord(**dr_prev)

        self.payload = DefaultReasonPayload(
            default_reason=DefaultReasonRecord(**payload["default_reason"]),
            default_reason_prev=default_reason_prev,
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
        if self.payload.default_reason_prev is None:
            self.validation_results.append(
                "Payload field 'default_reason_prev' is required"
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
        existing_reason = self._get_existing_record(self.payload.default_reason)
        if not self.status:
            return self.error

        if existing_reason is not None:
            return {
                "message": "Request payload validation error",
                "errors": ["This default reason exists in DB already."],
            }, 400

        updated_dr = self.payload.default_reason
        updated_dr.updated = datetime.now()
        updated_dr.is_active = True

        return self._store_dr_records([updated_dr])

    def put(self):
        existing_reason = self._get_existing_record(self.payload.default_reason)
        if not self.status:
            return self.error

        # guarranteed by payload validation
        assert self.payload.default_reason_prev is not None

        existing_reason_prev = self._get_existing_record(
            self.payload.default_reason_prev
        )
        if not self.status:
            return self.error

        # check if it is a regular undiscard update
        if existing_reason is not None and existing_reason_prev is not None:
            if (
                existing_reason.text,
                existing_reason.source,
                existing_reason.action,
            ) == (
                existing_reason_prev.text,
                existing_reason_prev.source,
                existing_reason_prev.action,
            ) and not existing_reason.is_active:
                updated_dr = self.payload.default_reason
                updated_dr.updated = datetime.now()
                updated_dr.is_active = True

                return self._store_dr_records([updated_dr])

        if existing_reason is not None:
            # check if both reason records are the same -> means just undiscard
            return {
                "message": "Request payload validation error",
                "errors": ["This default reason exists in DB already."],
            }, 400

        if existing_reason_prev is None:
            return {
                "message": "Request payload validation error",
                "errors": ["Previous default reason does not exist in DB."],
            }, 400
        elif not existing_reason_prev.is_active:
            return {
                "message": "Request payload validation error",
                "errors": ["Previous default reason is not active already."],
            }, 400

        updated_dr = self.payload.default_reason
        updated_dr.updated = datetime.now()
        updated_dr.is_active = True

        updated_prev_dr = self.payload.default_reason_prev
        updated_prev_dr.is_deleted = True

        return self._store_dr_records([updated_dr, updated_prev_dr])

    def delete(self):
        existing_reason = self._get_existing_record(self.payload.default_reason)
        if not self.status:
            return self.error

        if existing_reason is None:
            return {
                "message": "Request payload validation error",
                "errors": ["This default reason does not exist in DB."],
            }, 400
        elif not existing_reason.is_active:
            return {
                "message": "Request payload validation error",
                "errors": ["This default reason is not active already."],
            }, 400

        updated_dr = self.payload.default_reason
        updated_dr.updated = datetime.now()
        updated_dr.is_active = False

        return self._store_dr_records([updated_dr])

    def _get_existing_record(
        self, dr: DefaultReasonRecord
    ) -> Optional[DefaultReasonRecord]:
        self.status = False

        where_clause = (
            "WHERE dr_text = %(text)s "
            "AND dr_source = %(source)s "
            "AND dr_action = %(action)s"
        )

        response = self.send_sql_request(
            (
                self.sql.get_default_reasons_list.format(
                    where_clause=where_clause,
                    having_clause="",
                    order_by="",
                    limit="LIMIT 1",
                    offset="",
                ),
                {
                    "text": dr.text,
                    "source": dr.source,
                    "action": dr.action,
                },
            )
        )

        if not self.sql_status:
            return None

        self.status = True

        if not response:
            return None
        return DefaultReasonRecord(*response[0][:4])

    def _store_dr_records(self, dr_records: list[DefaultReasonRecord]):
        self.send_sql_request(
            (self.sql.store_default_reason, [r.to_sql() for r in dr_records])
        )

        if not self.sql_status:
            return self.error

        self.logger.info("All changes comitted to DB.")

        return {
            "request_args": self.args,
            "result": "OK",
            "default_reason": asdict(dr_records[0]),
        }, 200
