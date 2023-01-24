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
from flask import g
from ..sql import sql


class BlacklistedToken:

    def __init__(self, token: str, expires: int = None):
        self.token = token
        self.expires = expires
        self.conn = g.connection
        self.sql = sql

    def check_blacklist(self):
        self.conn.request_line = self.sql.get_token_from_blacklist.format(token=self.token)
        status, response = self.conn.send_request()

        if not status:
            return False

        if response[0][0] > 0:
            return True
        else:
            return False

    def post(self):
        json_ = [{
            "token": self.token,
            "expires_at": self.expires
        }]
        self.conn.request_line = (self.sql.insert_into_blacklisted_token, json_)

        status, response = self.conn.send_request()

        return status
