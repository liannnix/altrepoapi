# ALTRepo API
# Copyright (C) 2021-2022  BaseALT Ltd

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
import datetime
import jwt

from altrepo_api.api.base import APIWorker
from altrepo_api.settings import namespace
from ..sql import sql
from ...auth.auth import check_auth_ldap


class AuthLogin(APIWorker):
    """Authenticate an existing user and return an access token."""

    def __init__(self, connection, payload, **kwargs):
        self.conn = connection
        self.payload = payload
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        self.validation_results = []

        ldap_auth = check_auth_ldap(self.args["nickname"], self.args["password"], "packages_users")

        if ldap_auth.verified is False:
            self.validation_results.append(ldap_auth.error)

        if self.validation_results != []:
            return False
        else:
            return True

    def post(self):
        expires = {"hours": 1}
        payload = {
            "nickname": self.args["nickname"],
            "exp": datetime.datetime.now(tz=datetime.timezone.utc) + datetime.timedelta(**expires)
        }
        encoded_jwt = jwt.encode(payload, namespace.ADMIN_PASSWORD, algorithm="HS256")

        res = {
            "status": "success",
            "access_token": encoded_jwt,
            "expires": "1 hours"
        }
        return res, 201
