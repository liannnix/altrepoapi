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


def store_errata_user(
    conn: ConnectionProtocol, user: str, group: str, roles: list[str]
) -> tuple[bool, str]:
    # get original user name from DB using aliases table
    conn.request_line = sql.get_original_user_name.format(user=user)
    sql_status, response = conn.send_request()
    if not sql_status or not response:
        return False, f"Database error info: {response}"
    user = response[0][0]
    # store user data
    conn.request_line = sql.store_errata_user.format(
        user=user, group=group, roles=roles
    )
    sql_status, response = conn.send_request()
    if not sql_status:
        return False, f"Database error info: {response}"

    return True, ""


class UserRolesCache:
    def __init__(self, conn: ConnectionProtocol, logger: Logger):
        self.storage = STORAGE
        self.conn = conn
        self.logger = logger

    def add(
        self,
        user: str,
        display_name: str,
        group: str,
        roles: list[str],
        expires_in: int,
    ):
        user_data = {
            "user": user,
            "display_name": display_name,
            "group": group,
            "roles": roles,
        }

        # save to cache
        self.storage.map_set(
            name=USER_ROLES_KEY.format(user=user),
            mapping=user_data,
            expire=expires_in,
        )

        # store user data to the database
        status, message = store_errata_user(self.conn, user, group, roles)
        if not status:
            self.logger.error("Failed to store user data: %s", message)

    def get(self, user: str) -> dict[str, Any]:
        return self.storage.map_getall(USER_ROLES_KEY.format(user=user))
