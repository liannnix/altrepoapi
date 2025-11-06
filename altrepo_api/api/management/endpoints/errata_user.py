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

from typing import Optional

from altrepo_api.api.base import APIWorker, ConnectionProtocol, WorkerResult

from ..sql import sql

DEFAULT_LAST_ACTIVITIES_LIMIT = 10


class ErrataUserInfo(APIWorker):
    def __init__(
        self,
        conn: ConnectionProtocol,
        user: str,
    ) -> None:
        self.conn = conn
        self.user = user
        self.sql = sql
        super().__init__()

    def get(self) -> WorkerResult:
        response = self.send_sql_request(
            self.sql.get_errata_user.format(user=self.user)
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {"message": "No data not found in database"},
            )

        return {
            "user": response[0][0],
            "group": response[0][1],
            "roles": response[0][2],
            "aliases": response[0][3],
        }, 200


class ErrataUserTag(APIWorker):
    def __init__(self, conn: ConnectionProtocol, **kwargs) -> None:
        self.conn = conn
        self.kwargs = kwargs
        self.sql = sql
        super().__init__()

    def get(self) -> WorkerResult:
        input: str = self.kwargs["input"]
        limit: Optional[int] = self.kwargs["limit"]

        if not limit:
            limit = 5

        response = self.send_sql_request(
            self.sql.get_most_relevant_users.format(input=input, limit=limit)
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {"message": "No data not found in database"},
            )

        users = [{"user": r[0], "group": r[1]} for r in response]

        return {
            "request_args": self.kwargs,
            "length": len(users),
            "users": users,
        }, 200


class ErrataUserLastActivities(APIWorker):
    def __init__(
        self,
        conn: ConnectionProtocol,
        user: str,
        limit: Optional[int] = None,
    ) -> None:
        self.conn = conn
        self.user = user
        self.limit = limit or DEFAULT_LAST_ACTIVITIES_LIMIT
        self.sql = sql
        super().__init__()

    def get(self) -> WorkerResult:
        response = self.send_sql_request(
            self.sql.get_errata_user.format(user=self.user)
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error({"message": "No errata user found in database"})

        user = {
            "user": response[0][0],
            "group": response[0][1],
            "roles": response[0][2],
            "aliases": response[0][3],
        }

        response = self.send_sql_request(
            self.sql.get_user_last_activities.format(user=self.user, limit=self.limit)
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error({"message": "No data found in database"})

        return {
            "user": user,
            "activities": [
                {
                    "type": type,
                    "id": id,
                    "action": action,
                    "attr_type": attr_type,
                    "attr_link": attr_link,
                    "text": text,
                    "date": date,
                }
                for type, id, action, attr_type, attr_link, text, date in response
            ],
        }, 200
