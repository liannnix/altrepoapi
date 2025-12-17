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

import json
from datetime import datetime
from typing import Any, NamedTuple, Optional, Union

from altrepo_api.api.base import APIWorker, ConnectionProtocol, WorkerResult
from altrepo_api.api.misc import lut
from altrepo_api.api.parser import vuln_id_type, packager_nick_type
from altrepo_api.api.vulnerabilities.endpoints.common import CPE

from ..sql import sql


class VulnerabilityStatus(NamedTuple):
    vuln_id: str
    vs_author: str
    vs_status: str
    vs_reason: str
    vs_resolution: str
    vs_subscribers: list[str]
    vs_json: str
    vs_updated: datetime

    def asdict(self) -> dict[str, Any]:
        return {
            "vuln_id": self.vuln_id,
            "author": self.vs_author,
            "status": self.vs_status,
            "reason": self.vs_reason,
            "resolution": self.vs_resolution,
            "subscribers": self.vs_subscribers,
            "json": self.vs_json,
            "updated": self.vs_updated,
        }


class VulnStatus(APIWorker):
    def __init__(
        self,
        conn: ConnectionProtocol,
        args: Optional[dict[str, Any]] = None,
        payload: Optional[dict[str, Any]] = None,
    ) -> None:
        self.conn = conn
        self.args = args or {}
        self.payload = payload or {}
        self.vuln_id: str = self.args.get("vuln_id") or self.payload.get("vuln_id")  # type: ignore
        self.sql = sql
        super().__init__()

    def _check_vuln_id(self) -> bool:
        try:
            vuln_id_type(self.vuln_id)
        except ValueError:
            return False

        return True

    def _check_vuln_exists(self) -> None:
        response = self.send_sql_request(
            sql.get_count_distinct_by_vuln_id.format(vuln_id=self.vuln_id)
        )
        if not self.sql_status:
            raise RuntimeError(self.error[0])

        if not response or response[0][0] != 1:
            self.store_error(
                {"message": "No vulnerability found"},
                http_code=404,
            )
            raise RuntimeError(self.error[0])

    def _check_json(self) -> bool:
        try:
            vs_json = json.loads(self.payload.get("json", "{}"))
        except json.JSONDecodeError as exc:
            self.validation_results.append(f"Failed to decode 'json': {exc}")
            return False

        for key in vs_json:
            if key not in lut.vuln_status_json_fields:
                self.validation_results.append(f"Unsupported 'vs_json' field: {key}")

        if json_cpe_str := vs_json.get("cpe"):
            try:
                CPE(json_cpe_str)
            except ValueError as exc:
                self.validation_results.append(f"Bad value in 'vs_json.cpe': {exc}")

        return self.validation_results == []

    def _create_vuln_status(self) -> VulnerabilityStatus:
        return VulnerabilityStatus(
            vuln_id=self.vuln_id,
            vs_author=self.payload.get("author", ""),
            vs_status=self.payload.get("status", lut.vuln_status_statuses[0]),
            vs_resolution=self.payload.get("resolution", ""),
            vs_reason=self.payload.get("reason", ""),
            vs_subscribers=sorted(self.payload.get("subscribers", [])),
            vs_json=self.payload.get("json", "{}"),
            vs_updated=self.payload.get("updated", datetime.now()),
        )

    def _get_vuln_status(self) -> Union[VulnerabilityStatus, None]:
        response = self.send_sql_request(
            sql.get_vuln_status_by_vuln_id.format(vuln_id=self.vuln_id)
        )
        if not self.sql_status:
            raise RuntimeError(self.error[0])
        if not response:
            return None

        return VulnerabilityStatus(*response[0])

    def _store_vuln_status(self, vuln_status: VulnerabilityStatus) -> None:
        amount_of_inserted = self.send_sql_request(
            (sql.store_vuln_status, [vuln_status._asdict()])
        )
        if not self.sql_status:
            raise RuntimeError(self.error[0])
        if amount_of_inserted != 1:
            self.store_error(
                {"message": "Vulnerability status has not been stored"},
                http_code=400,
            )
            raise RuntimeError(self.error[0])

    def check_params_get(self) -> bool:
        self.logger.info("GET args: %s", self.args)
        return True

    def get(self) -> WorkerResult:
        try:
            self._check_vuln_exists()

            if old_vuln_status := self._get_vuln_status():
                return old_vuln_status.asdict(), 200

            new_vuln_status = self._create_vuln_status()
            self._store_vuln_status(new_vuln_status)
        except RuntimeError:
            return self.error

        return new_vuln_status.asdict(), 200

    def check_params_post(self) -> bool:
        self.logger.info("POST payload: %s", self.payload)

        status: Optional[str] = self.payload.get("status")
        resolution: Optional[str] = self.payload.get("resolution")
        reason: Optional[str] = self.payload.get("reason")
        subscribers: Optional[str] = self.payload.get("subscribers")

        if not self._check_vuln_id():
            self.validation_results.append(f"Invalid vulnerability ID: {self.vuln_id}")

        if status == "resolved" and resolution is None:
            self.validation_results.append("No resolution for resolved status")

        if (status is None or status != "resolved") and resolution is not None:
            self.validation_results.append(
                "Resolution is allowed when status is 'resolved'"
            )

        if resolution and not reason:
            self.validation_results.append("No reason for resolution")

        if subscribers is not None:
            for subscriber in subscribers:
                try:
                    packager_nick_type(subscriber)
                except ValueError:
                    self.validation_results.append(f"Invalid nickname: {subscriber}")

        self._check_json()

        return self.validation_results == []

    def post(self) -> WorkerResult:
        status_order = {
            status: order for order, status in enumerate(lut.vuln_status_statuses)
        }

        try:
            self._check_vuln_exists()
            old_vuln_status = self._get_vuln_status()
            new_vuln_status = self._create_vuln_status()

            if old_vuln_status is None:
                if new_vuln_status.vs_status != "new":
                    new_vuln_status = new_vuln_status._replace(
                        vs_subscribers=sorted(
                            [
                                *new_vuln_status.vs_subscribers,
                                new_vuln_status.vs_author,
                            ]
                        )
                    )
                self._store_vuln_status(new_vuln_status)
                return new_vuln_status.asdict(), 201

            if old_vuln_status[:-1] == new_vuln_status[:-1]:
                return self.store_error(
                    {"message": "No changes"},
                    http_code=409,
                )

            if (
                old_vuln_status.vs_status != "new"
                and new_vuln_status.vs_status == "new"
            ):
                return self.store_error(
                    {"message": "Can't return status to 'new'"},
                    http_code=409,
                )

            for attr in VulnerabilityStatus._fields:
                if getattr(old_vuln_status, attr) != getattr(new_vuln_status, attr):
                    new_vuln_status.vs_subscribers.append(new_vuln_status.vs_author)
                    break

            if (
                status_order[old_vuln_status.vs_status]
                > status_order[new_vuln_status.vs_status]
            ):
                if new_vuln_status.vs_reason is None or new_vuln_status.vs_status == "":
                    return self.store_error(
                        {"message": "No reason for status returning back"},
                        http_code=409,
                    )

            self._store_vuln_status(new_vuln_status)
        except RuntimeError:
            return self.error

        return new_vuln_status.asdict(), 200
