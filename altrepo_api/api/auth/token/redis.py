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

import redis

from redis import __version__ as REDIS_VERSION
from packaging import version
from typing import Any, Optional, Union

REDIS_BREAKING_CHANGE_VERSION = "3.4.1"


def decode_map(mapping: dict[bytes, bytes]) -> dict[str, str]:
    return {k.decode(): v.decode() for k, v in mapping.items()}


class RedisStorage:
    def __init__(self, url: str, db: int = 0):
        self.conn = redis.from_url(url=url, db=db)

    def delete(self, name: str) -> None:
        """Deletes value from storage by name."""

        self.conn.delete(name)

    def map_delete(self, name: str, key: str) -> None:
        """Deletes value from mapping in storage by name and key."""

        self.conn.hdel(name, key)

    def map_getall(self, name: str) -> dict[str, str]:
        """Retrives mapping from storage by name."""

        return decode_map(self.conn.hgetall(name))

    def map_get(self, name: str, key: str) -> Union[str, None]:
        """Retrives mapping value from storage by name and key."""

        res = self.conn.hget(name, key)

        if res is not None:
            return res.decode()

        return None

    def map_set(
        self,
        name: str,
        mapping: dict[str, Any],
        expire: Optional[int] = None,
    ) -> None:
        """Saves mapping to storage and set expiration time."""

        redis_version = version.parse(REDIS_VERSION)
        if redis_version > version.parse(REDIS_BREAKING_CHANGE_VERSION):
            self.conn.hset(name, mapping=mapping)  # type: ignore
        else:
            self.conn.hmset(name, mapping=mapping)  # type: ignore

        if expire is not None:
            self.conn.expire(name, expire)
