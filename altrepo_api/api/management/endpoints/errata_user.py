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

from datetime import datetime
from typing import Any, NamedTuple, Optional

from altrepo_api.api.base import APIWorker, ConnectionProtocol, WorkerResult
from altrepo_api.api.parser import (
    errata_id_type,
    pkg_name_type,
    vuln_id_type,
    packager_nick_type,
)

from ..sql import sql

DEFAULT_LAST_ACTIVITIES_LIMIT = 10


class UserAliases(NamedTuple):
    name: Optional[str] = None
    aliases: Optional[list[str]] = None


class ErrataUserAliases(APIWorker):
    def __init__(self, conn: ConnectionProtocol, **kwargs) -> None:
        self.conn = conn
        self.kwargs = kwargs
        self.sql = sql
        self.ua: UserAliases
        super().__init__()

    def check_params(self) -> bool:
        self.ua = UserAliases(**self.kwargs)
        self.logger.debug(f"args : {self.kwargs}")

        if self.ua.name is not None and not self.ua.name:
            self.validation_results.append("User name should be a non empty string")

        return self.validation_results == []

    def check_params_post(self) -> bool:
        self.ua = UserAliases(**self.kwargs)
        self.logger.debug(f"args : {self.kwargs}")

        if self.ua.name is not None and not self.ua.name:
            self.validation_results.append("User name should be a non empty string")

        if self.ua.aliases is None:
            self.ua = self.ua._replace(aliases=[])
        else:
            for alias in self.ua.aliases:
                if not alias:
                    self.validation_results.append("Alias should be a non empty string")
            # sort list of aliases for DB consistency
            self.ua = self.ua._replace(aliases=sorted(self.ua.aliases))

        return self.validation_results == []

    def get(self) -> WorkerResult:
        where_clause = "" if self.ua.name is None else f"WHERE user = '{self.ua.name}'"

        response = self.send_sql_request(
            self.sql.get_user_aliases.format(
                where_clause=where_clause, having_clause=""
            )
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {"message": "No data not found in database"},
            )

        users = [{"name": r[0], "aliases": r[1]} for r in response]

        return {
            "request_args": self.kwargs,
            "length": len(users),
            "users": users,
        }, 200

    def post(self) -> WorkerResult:
        having_clause = f"HAVING has(aka, '{self.ua.name}')"

        if self.ua.aliases:
            having_clause += f" OR has({self.ua.aliases}, user)"

        response = self.send_sql_request(
            self.sql.get_user_aliases.format(
                where_clause="", having_clause=having_clause
            )
        )
        if not self.sql_status:
            return self.error
        if response:
            for existing_alias in (UserAliases(*el) for el in response):
                if self.ua.name == existing_alias.name:
                    # existing record is equal to a given one
                    if self.ua.aliases == existing_alias.aliases:
                        return "OK", 200
                    # we just update and existing aliases record
                    continue
                # existing aliases contains given original user name
                if existing_alias.aliases and self.ua.name in existing_alias.aliases:
                    return self.store_error(
                        {
                            "message": f"User '{existing_alias.name}' already has this alias: '{self.ua.name}'"
                        },
                        http_code=409,
                    )
                # given aliases contains existing orignal user name
                if self.ua.aliases and existing_alias.name in self.ua.aliases:
                    return self.store_error(
                        {
                            "message": (
                                f"User '{existing_alias.name}' already exists "
                                f"and cannot be used as an alias for '{self.ua.name}'"
                            )
                        },
                        http_code=409,
                    )

        # store new user aliases
        response = self.send_sql_request(
            (
                self.sql.store_user_aliases,
                [
                    (self.ua.name, self.ua.aliases),
                ],
            )
        )
        if not self.sql_status:
            return self.error

        return "OK", 200


class ErrataUserInfo(APIWorker):
    def __init__(self, conn: ConnectionProtocol, **kwargs) -> None:
        self.conn = conn
        self.kwargs = kwargs
        self.sql = sql
        super().__init__()

    def check_params(self) -> bool:
        self.logger.debug("args: %s", self.kwargs)

        user_name = self.kwargs["name"]

        try:
            packager_nick_type(user_name)
        except ValueError:
            self.validation_results.append(f"Invalid nickname: {user_name}")

        return self.validation_results == []

    def get(self) -> WorkerResult:
        response = self.send_sql_request(
            self.sql.get_errata_user.format(user=self.kwargs["name"])
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
    def __init__(self, conn: ConnectionProtocol, **kwargs) -> None:
        self.conn = conn
        self.kwargs = kwargs
        self.sql = sql
        super().__init__()

    def check_params(self) -> bool:
        self.logger.debug("args: %s", self.kwargs)

        user_name = self.kwargs["name"]

        try:
            packager_nick_type(user_name)
        except ValueError:
            self.validation_results.append(f"Invalid nickname: {user_name}")

        return self.validation_results == []

    def get(self) -> WorkerResult:
        response = self.send_sql_request(
            self.sql.get_errata_user.format(user=self.kwargs["name"])
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
            self.sql.get_user_last_activities.format(
                user=user["user"],
                limit=self.kwargs["limit"] or DEFAULT_LAST_ACTIVITIES_LIMIT,
            )
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


class ErrataUserSubscriptions(APIWorker):
    def __init__(self, conn: ConnectionProtocol, payload: dict[str, Any]) -> None:
        self.conn = conn
        self.payload = payload
        self.sql = sql
        super().__init__()

    def check_params(self) -> bool:
        self.logger.debug("payload: %s", self.payload)

        user_name = self.payload["name"]

        try:
            packager_nick_type(user_name)
        except ValueError:
            self.validation_results.append(f"Invalid nickname: {user_name}")

        return self.validation_results == []

    def get(self) -> WorkerResult:
        response = self.send_sql_request(
            self.sql.get_original_user_name.format(user=self.payload["name"])
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error({"message": "No errata user found in database"})

        response = self.send_sql_request(
            self.sql.get_errata_user_active_subscriptions.format(user=response[0][0])
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error({"message": "No data found in database"})

        return {
            "subscriptions": [
                {
                    "user": user,
                    "entity_type": entity_type,
                    "entity_link": entity_link,
                    "state": state,
                    "assigner": assigner,
                    "date": date,
                }
                for user, entity_type, entity_link, state, assigner, date in response
            ]
        }, 200

    def check_params_post(self) -> bool:
        self.logger.debug("payload: %s", self.payload)

        user_name = self.payload["name"]

        try:
            packager_nick_type(user_name)
        except ValueError:
            self.validation_results.append(f"Invalid nickname: {user_name}")

        assigner = self.payload["assigner"]
        entity_type = self.payload["entity_type"]
        entity_link = self.payload["entity_link"]

        try:
            packager_nick_type(assigner)
        except ValueError:
            self.validation_results.append(f"Invalid nickname: {assigner}")

        for type, predicate, err_template in [
            ("vuln", vuln_id_type, "Invalid vulnerability ID: {}"),
            ("package", pkg_name_type, "Invalid package name: {}"),
            ("errata", errata_id_type, "Invalid errata ID: {}"),
        ]:
            if entity_type == type:
                try:
                    predicate(entity_link)
                except ValueError:
                    self.validation_results.append(err_template.format(entity_link))

        return self.validation_results == []

    def post(self) -> WorkerResult:
        response = self.send_sql_request(
            self.sql.get_original_user_name.format(user=self.payload["name"])
        )
        if not self.sql_status:
            return self.error

        original_user = response[0][0]

        response = self.send_sql_request(
            self.sql.get_original_user_name.format(user=self.payload["assigner"])
        )
        if not self.sql_status:
            return self.error

        original_assigner = response[0][0]

        new_subscription = {
            "user": original_user,
            "entity_type": self.payload["entity_type"],
            "entity_link": self.payload["entity_link"],
            "state": self.payload["state"],
            "assigner": original_assigner,
            "date": datetime.now(),
        }

        response = self.send_sql_request(
            self.sql.get_errata_user_active_subscription.format(
                user=original_user,
                entity_type=self.payload["entity_type"],
                entity_link=self.payload["entity_link"],
            )
        )
        if not self.sql_status:
            return self.error
        if not response:
            # if no previous subscription on the entity
            if self.payload["state"] == "inactive":
                return self.store_error(
                    {"message": "Can't unsubscribe from non existing entity"}
                )

            amount_of_inserted = self.send_sql_request(
                (
                    self.sql.store_errata_user_subscription,
                    [new_subscription],
                )
            )
            if amount_of_inserted != 1:
                self.store_error({"message": "Failed to subscribe user"})

            return new_subscription, 201

        old_subscription = {
            "user": response[0][0],
            "entity_type": response[0][1],
            "entity_link": response[0][2],
            "state": response[0][3],
            "assigner": response[0][4],
            "date": response[0][5],
        }

        if (
            (old_subscription["user"] == old_subscription["assigner"])
            and (old_subscription["assigner"] != new_subscription["assigner"])
            and (old_subscription["state"] != new_subscription["state"])
        ):
            return self.store_error(
                {"message": "Can't change self-subscription"},
                http_code=409,
            )

        subscriptions = [new_subscription]

        if (new_subscription["user"] == new_subscription["assigner"]) and (
            old_subscription["assigner"] != new_subscription["assigner"]
        ):
            old_subscription["state"] = "inactive"
            subscriptions.append(old_subscription)

        amount_of_inserted = self.send_sql_request(
            (self.sql.store_errata_user_subscription, subscriptions)
        )
        if amount_of_inserted != 1:
            self.store_error({"message": "Failed to subscribe user"})

        return new_subscription, 201
