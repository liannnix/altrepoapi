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
from altrepo_api.api.base import APIWorker
from .blacklisted_token import BlacklistedToken
from ..sql import sql


class AuthLogout(APIWorker):
    """Authenticate an existing user and return an access token."""

    def __init__(self, connection, payload, **kwargs):
        self.conn = connection
        self.payload = payload
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        return True

    def post(self):
        status = BlacklistedToken(self.args["token"], self.args["exp"]).post()

        if not status:
            return "Failed to log out", 400

        return "you successfully logged out", 201
