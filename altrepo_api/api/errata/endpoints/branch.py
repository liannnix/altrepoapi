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

from altrepo_api.utils import sort_branches

from altrepo_api.api.base import APIWorker
from altrepo_api.api.parser import errata_id_type

from .common import (
    BranchUpdate,
    get_erratas_by_ids,
    get_packges_updates_erratas,
    ERRATA_BRANCH_BULLETIN_PREFIX,
    BRANCH_UPDATE_MAX_BATCH,
)
from ..sql import sql


class BranchesUpdates(APIWorker):
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
            if not errata_id.startswith(ERRATA_BRANCH_BULLETIN_PREFIX):
                self.validation_results.append(
                    f"not a branch update errata: {errata_id}"
                )
                break

        if len(self.errata_ids) > BRANCH_UPDATE_MAX_BATCH:
            self.validation_results.append(
                "Request payload size is too big. "
                f"Max errata_ids list size is {BRANCH_UPDATE_MAX_BATCH}"
            )

        if self.validation_results != []:
            return False

        return True

    def post(self):
        # get branch update erratas
        bu_erratas = get_erratas_by_ids(self, self.errata_ids)
        if not self.status:
            return self.error
        if bu_erratas is None:
            return self.store_error(
                {"message": f"No errata data found for {self.errata_ids}"}
            )

        # get referenced package update erratas
        pu_erratas = [ref.id for bu in bu_erratas for ref in bu.references]
        packages_updates = get_packges_updates_erratas(self, pu_erratas)
        if not self.status:
            return self.error
        if packages_updates is None:
            return self.store_error(
                {"message": f"No errata data found for {pu_erratas}"}
            )

        pu_map = {
            package_update.errata.id.id: package_update
            for package_update in packages_updates
        }

        # build branch updates
        branches_updates = [
            BranchUpdate(
                errata=errata,
                packages_updates=[
                    pu_map[pu_id] for pu_id in (ref.id for ref in errata.references)
                ],
            )
            for errata in bu_erratas
        ]

        return {"branches_updates": [bu.asdict() for bu in branches_updates]}, 200


class ErrataBranches(APIWorker):
    """Get branches list from errata history."""

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def get(self):
        response = self.send_sql_request(self.sql.get_errata_branches)
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {"message": "No data not found in database"},
            )

        branches = [branch for branch in sort_branches([el[0] for el in response])]

        return {"length": len(branches), "branches": branches}, 200
