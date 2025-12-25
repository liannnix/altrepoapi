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

import json

from datetime import datetime
from enum import IntEnum
from typing import Any, NamedTuple

from altrepo_api.api.misc import lut
from .constants import ERRAT_CHANGE_ACTOR_DEFAULT


class UserInfo(NamedTuple):
    name: str
    ip: str


class Reference(NamedTuple):
    type: str
    link: str

    def asdict(self) -> dict[str, Any]:
        return self._asdict()


class ChangeType(IntEnum):
    CREATE = 0
    UPDATE = 1
    DISCARD = 2
    HIDE = 3
    SHOW = 4


class ChangeReason(NamedTuple):
    # actor: str
    user: UserInfo
    message: str
    details: dict[str, Any]

    def serialize(self) -> str:
        res = self._asdict()
        res["actor"] = ERRAT_CHANGE_ACTOR_DEFAULT
        res["user"] = self.user._asdict()
        return json.dumps(res, default=str)


class PncRecord(NamedTuple):
    pkg_name: str
    pnc_state: str
    pnc_result: str
    pnc_type: str
    pnc_source: str

    def asdict(self) -> dict[str, str]:
        return self._asdict()


class PncPackage(NamedTuple):
    pkg_name: str
    pnc_type: str
    pnc_source: str

    def asdict(self):
        res = self._asdict()
        res["pnc_type"] = lut.repology_reverse_branch_map[res["pnc_type"]][0]
        return res


class PncListElement(NamedTuple):
    pnc_state: str
    pnc_result: str
    packages: list[PncPackage]

    def asdict(self) -> dict[str, str]:
        res = self._asdict()
        res["packages"] = [r.asdict() for r in self.packages]
        res["cpes"] = []
        return res


class Comment(NamedTuple):
    comment_id: int
    comment_pid: int
    comment_rid: int
    comment_entity_type: str
    comment_entity_link: str
    comment_author: str
    comment_text: str
    comment_references: list[Reference]
    comment_created: datetime

    def asdict(self) -> dict[str, str]:
        res = self._asdict()
        res["comment_references"] = [r.asdict() for r in self.comment_references]
        res["comment_created"] = self.comment_created.isoformat()
        return res


class CommentListElement(NamedTuple):
    comment: Comment
    is_discarded: bool

    def asdict(self) -> dict[str, str]:
        res = self.comment._asdict()
        res["id"] = str(self.comment.comment_id)
        res["pid"] = str(self.comment.comment_pid)
        res["rid"] = str(self.comment.comment_rid)
        res["comment_references"] = [
            Reference(r[0], r[1]).asdict() for r in self.comment.comment_references
        ]
        res["comment_created"] = self.comment.comment_created.isoformat()
        res["is_discarded"] = self.is_discarded
        return res


class CommentChangeRecord(NamedTuple):
    reason: ChangeReason
    action: ChangeType
    comment_id: int

    def asdict(self) -> dict[str, Any]:
        res = {}
        res["cc_user"] = self.reason.user.name
        res["cc_user_ip"] = self.reason.user.ip
        res["cc_reason"] = self.reason.message
        res["cc_action"] = self.action.value
        res["comment_id"] = self.comment_id
        return res
