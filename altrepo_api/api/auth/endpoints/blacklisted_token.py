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
import jwt
import redis
from flask import request

from altrepo_api.settings import namespace
from altrepo_api.utils import get_fingerprint_to_md5
from ..constants import BLACKLISTED_ACCESS_TOKEN_KEY


class BlacklistedAccessToken:
    def __init__(self, token: str, expires: int):
        self.token = token
        self.expires = expires
        self.conn_redis = redis.from_url(namespace.REDIS_URL, db=0)

    def check_blacklist(self):
        """
        Check the access token in the blacklist.
        if the fingerprint of the current user does not
        match the fingerprint of the access token, then
        add the token to the blacklist
        """
        if not self.get_token_from_blacklist():
            token_payload = jwt.decode(
                self.token, namespace.ADMIN_PASSWORD, algorithms=["HS256"]
            )
            check = self.check_fingerprint(token_payload.get("fingerprint", None))
            if not check:
                return True
            else:
                return False
        else:
            return True

    def check_fingerprint(self, fingerprint):
        """
        Check the fingerprint of the current user and
        the fingerprint of the access token.
        """
        current_fingerprint = get_fingerprint_to_md5(request)
        if fingerprint != current_fingerprint:
            self.write_to_blacklist()
            return False
        else:
            return True

    def write_to_blacklist(self):
        """
        Write access token in the blacklist.
        """
        self.conn_redis.hmset(
            BLACKLISTED_ACCESS_TOKEN_KEY.format(token=self.token),
            {"expires_at": self.expires},
        )
        self.conn_redis.expire(
            BLACKLISTED_ACCESS_TOKEN_KEY.format(token=self.token),
            namespace.EXPIRES_ACCESS_TOKEN,
        )

    def get_token_from_blacklist(self):
        token = self.conn_redis.hgetall(
            BLACKLISTED_ACCESS_TOKEN_KEY.format(token=self.token)
        )
        return token
