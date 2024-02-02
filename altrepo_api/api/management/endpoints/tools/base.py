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

import json

from datetime import datetime
from enum import IntEnum
from typing import Any, NamedTuple, Protocol, Union
from uuid import UUID

from .constants import CHANGE_SOURCE_AUTO, CHANGE_SOURCE_MANUAL


class ErrataManageError(Exception):
    pass


class PncManageError(Exception):
    pass


class DBTransactionRollback(Protocol):
    """Callback that rolls back DB changes using list transaction IDs."""

    def __call__(self, transaction_ids: list[UUID]) -> bool:
        ...


class Task(NamedTuple):
    id: int
    prev: int
    date: datetime


class TaskInfo(NamedTuple):
    pkg_hash: int
    pkg_name: str
    pkg_version: str
    pkg_release: str
    pkgset_name: str
    task_id: int
    subtask_id: int
    task_state: str


class Branch(NamedTuple):
    name: str
    date: datetime
    task: int


class UserInfo(NamedTuple):
    name: str
    ip: str


class ErrataID(NamedTuple):
    """ErrataID object class"""

    id: str
    prefix: str
    year: int
    number: int
    version: int

    @staticmethod
    def from_id(id: str) -> "ErrataID":
        """Creates an ErrataID object from string representation."""

        _parts = id.split("-")

        return ErrataID(
            id=id,
            prefix="-".join(_parts[:2]),
            year=int(_parts[2]),
            number=int(_parts[3]),
            version=int(_parts[4]),
        )

    def __str__(self):
        return self.id

    @property
    def _compare_key(self):
        # ignore prefix due to (year, number) tuple is guaranteed to be uniq
        return (self.year, self.number, self.version)

    def _compare(self, other: "ErrataID", method) -> bool:
        if not isinstance(other, ErrataID):
            return NotImplemented

        return method(self._compare_key, other._compare_key)

    def __eq__(self, other: "ErrataID") -> bool:
        return self._compare(other, lambda s, o: s == o)

    def __ne__(self, other: "ErrataID") -> bool:
        return self._compare(other, lambda s, o: s != o)

    def __lt__(self, other: "ErrataID") -> bool:
        return self._compare(other, lambda s, o: s < o)

    def __le__(self, other: "ErrataID") -> bool:
        return self._compare(other, lambda s, o: s <= o)

    def __gt__(self, other: "ErrataID") -> bool:
        return self._compare(other, lambda s, o: s > o)

    def __ge__(self, other: "ErrataID") -> bool:
        return self._compare(other, lambda s, o: s >= o)

    @property
    def no_version(self) -> str:
        return f"{self.prefix}-{self.year}-{self.number}"


class Reference(NamedTuple):
    type: str
    link: str

    def asdict(self) -> dict[str, Any]:
        return self._asdict()


class Errata(NamedTuple):
    id: Union[ErrataID, None]
    type: str
    source: str
    created: datetime
    updated: datetime
    pkg_hash: int
    pkg_name: str
    pkg_version: str
    pkg_release: str
    pkgset_name: str
    task_id: int
    subtask_id: int
    task_state: str
    references: list[Reference]
    hash: int
    is_discarded: bool = False

    def asdict(self) -> dict[str, Any]:
        res = self._asdict()
        res["id"] = self.id.id if self.id else ""
        res["created"] = self.created.isoformat()
        res["updated"] = self.updated.isoformat()
        res["references"] = [r.asdict() for r in self.references]
        res["pkg_hash"] = str(self.pkg_hash)
        res["hash"] = str(self.hash)
        return res

    def update(self, **kwargs) -> "Errata":
        res = self._asdict()

        # check keywords are all valid
        for k in kwargs:
            if k not in self._fields:
                raise ValueError(
                    "Class %s has not attribute %s" % (self.__class__.__name__, k)
                )

        res.update(kwargs)

        # handle `id` filed update
        _id = res["id"]
        if isinstance(_id, str):
            res["id"] = ErrataID.from_id(_id)

        return Errata(**res)

    def __str__(self) -> str:
        return str(self.asdict())


class ChangeType(IntEnum):
    CREATE = 0
    UPDATE = 1
    DISCARD = 2
    HIDE = 3
    SHOW = 4


class ChangeSource(IntEnum):
    AUTO = 0
    MANUAL = 1

    @staticmethod
    def from_string(v: str) -> "ChangeSource":
        if v == CHANGE_SOURCE_AUTO:
            return ChangeSource.AUTO
        if v == CHANGE_SOURCE_MANUAL:
            return ChangeSource.MANUAL
        return ChangeSource.MANUAL


class ChangeOrigin(IntEnum):
    PARENT = 0
    CHILD = 1


class ChangeReason(NamedTuple):
    actor: UserInfo
    message: str
    details: dict[str, Any]

    def serialize(self) -> str:
        res = self._asdict()
        res["actor"] = f"{self.actor.name}[{self.actor.ip}]"
        return json.dumps(res, default=str)


class ErrataChange(NamedTuple):
    id: ErrataID
    created: datetime
    updated: datetime
    user: str
    user_ip: str
    reason: ChangeReason
    type: ChangeType
    source: ChangeSource
    origin: ChangeOrigin
    errata_id: ErrataID
    transaction_id: UUID

    def asdict(self) -> dict[str, Any]:
        res = self._asdict()
        res["id"] = self.id.id
        res["errata_id"] = self.errata_id.id
        res["created"] = self.created.isoformat()
        res["updated"] = self.updated.isoformat()
        res["type"] = self.type.name
        res["source"] = self.source.name
        res["origin"] = self.origin.name
        res["reason"] = self.reason.serialize()
        return res


class PncRecord(NamedTuple):
    pkg_name: str
    pnc_state: str
    pnc_result: str
    pnc_type: str
    pnc_source: str

    def asdict(self) -> dict[str, str]:
        return self._asdict()


class PncChangeRecord(NamedTuple):
    id: UUID
    reason: ChangeReason
    type: ChangeType
    source: ChangeSource
    origin: ChangeOrigin
    pnc: PncRecord

    def asdict(self) -> dict[str, Any]:
        res = self._asdict()
        res["id"] = str(self.id)
        res["type"] = self.type.name
        res["source"] = self.source.name
        res["origin"] = self.origin.name
        res["pnc"] = self.pnc._asdict()
        res["reason"] = self.reason.serialize()
        res["user"] = self.reason.actor.name
        res["user_ip"] = self.reason.actor.ip
        return res
