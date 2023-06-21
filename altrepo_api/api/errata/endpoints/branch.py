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

from altrepo_api.api.base import APIWorker
from altrepo_api.api.parser import errata_id_type

from .common import (
    BranchUpdate,
    get_erratas_by_ids,
    get_packges_updates_erratas,
    ERRATA_BRANCH_BULLETIN_PREFIX,
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
            package_update.errata.id: package_update
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
