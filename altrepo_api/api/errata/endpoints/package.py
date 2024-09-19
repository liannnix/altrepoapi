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

from altrepo_api.api.base import APIWorker

from altrepo_api.api.parser import errata_id_type

from .common import (
    get_packges_updates_erratas,
    ERRATA_PACKAGE_UPDATE_PREFIX,
    PACKAGE_UPDATE_MAX_BATCH,
)
from ..sql import sql


class PackagesUpdates(APIWorker):
    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        self.errata_ids: list[str] = []
        super().__init__()

    def check_params(self):
        try:
            errata_ids: list[str] = self.args["json_data"]["errata_ids"]
        except (TypeError, KeyError):
            self.validation_results.append("Payload data parsing error")
            return False

        if not errata_ids:
            self.validation_results.append("At least one Errata ID should be provided")
            return False

        for errata_id in errata_ids:
            try:
                self.errata_ids.append(errata_id_type(errata_id))
            except ValueError:
                self.validation_results.append(f"invalid errata id: {errata_id}")
                break
            if not errata_id.startswith(ERRATA_PACKAGE_UPDATE_PREFIX):
                self.validation_results.append(
                    f"not a package update errata: {errata_id}"
                )
                break

        if len(self.errata_ids) > PACKAGE_UPDATE_MAX_BATCH:
            self.validation_results.append(
                "Request payload size is too big. "
                f"Max errata_ids list size is {PACKAGE_UPDATE_MAX_BATCH}"
            )

        if self.validation_results != []:
            return False

        return True

    def post(self):
        packages_updates = get_packges_updates_erratas(self, self.errata_ids)

        if not self.status or packages_updates is None:
            return self.error

        return {"packages_updates": [p.asdict() for p in packages_updates]}, 200
