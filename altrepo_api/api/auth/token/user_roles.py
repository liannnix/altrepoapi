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

from logging import Logger
from typing import Any

from altrepo_api.api.base import ConnectionProtocol

from ..constants import USER_ROLES_KEY
from ..sql import sql
from .token import STORAGE


class UserRolesCache:
    def __init__(self, conn: ConnectionProtocol, logger: Logger):
        self.storage = STORAGE
        self.conn = conn
        self.logger = logger

    def add(self, user: str, group: str, roles: list[str], expires_in: int):
        user_data = {"user": user, "group": group, "roles": roles}

        # save to cache
        self.storage.map_set(
            name=USER_ROLES_KEY.format(user=user),
            mapping=user_data,
            expire=expires_in,
        )

        # and to the database
        self.conn.request_line = sql.store_errata_user.format(**user_data)
        sql_status, response = self.conn.send_request()

        if not sql_status:
            self.logger.error("Database insertion error for %s", user_data)
            self.logger.error("Database error info: %s", response)

    def get(self, user: str) -> dict[str, Any]:
        return self.storage.map_getall(USER_ROLES_KEY.format(user=user))
