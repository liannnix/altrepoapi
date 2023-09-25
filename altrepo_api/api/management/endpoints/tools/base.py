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

from datetime import datetime
from enum import IntEnum
from typing import Any, NamedTuple, Union


class ErrataManageError(Exception):
    pass


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

    def asdict(self) -> dict[str, Any]:
        res = self._asdict()
        res["id"] = self.id.id if self.id else ""
        res["created"] = self.created.isoformat()
        res["updated"] = self.updated.isoformat()
        res["references"] = [r.asdict() for r in self.references]
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


class ErrataChangeType(IntEnum):
    CREATE = 0
    UPDATE = 1
    DISCARD = 2
    HIDE = 3
    SHOW = 4


class ErrataChangeSource(IntEnum):
    AUTO = 0
    MANUAL = 1


class ErrataChangeOrigin(IntEnum):
    PARENT = 0
    CHILD = 1


class ErrataChange(NamedTuple):
    id: ErrataID
    created: datetime
    updated: datetime
    user: str
    user_ip: str
    reason: str
    type: ErrataChangeType
    source: ErrataChangeSource
    origin: ErrataChangeOrigin
    errata_id: ErrataID

    def asdict(self) -> dict[str, Any]:
        res = self._asdict()
        res["id"] = self.id.id
        res["errata_id"] = self.errata_id.id
        res["created"] = self.created.isoformat()
        res["updated"] = self.updated.isoformat()
        res["type"] = self.type.name
        res["source"] = self.source.name
        res["origin"] = self.origin.name
        return res
