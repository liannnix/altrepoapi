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

# from altrepo_api.api.misc import lut

from ..sql import sql
from .common import VulnerabilityInfo


class VulnInfo(APIWorker):
    """Retrieves vulnerability information by id."""

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        return True

    def get(self):
        vuln_id = self.args["vuln_id"]

        response = self.send_sql_request(
            self.sql.get_vuln_info_by_ids.format(
                tmp_table=(vuln_id,), json_field="vuln_json"
            )
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {"message": f"No data info found in DB for {vuln_id}"}
            )

        vuln = VulnerabilityInfo(*response[0][1:])

        return {
            "request_args": self.args,
            "vuln_info": vuln.asdict(),
        }, 200
