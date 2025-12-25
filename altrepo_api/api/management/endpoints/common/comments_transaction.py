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

from dataclasses import dataclass

from altrepo_api.utils import get_logger

from .base import ChangeReason, ChangeType, CommentChangeRecord, Comment

logger = get_logger(__name__)


@dataclass
class CommentUpdate:
    comment: Comment
    action: ChangeType


def _build_comment_change(
    *,
    comment_id: int,
    reason: ChangeReason,
    action: ChangeType,
) -> CommentChangeRecord:
    logger.info(
        f"Build `Comments` change history record: {comment_id} " f"[{action.name}]"
    )
    return CommentChangeRecord(
        comment_id=comment_id,
        reason=reason,
        action=action,
    )


class Transaction:
    def __init__(self) -> None:
        self._reason: ChangeReason
        self._comment_updates: CommentUpdate
        self._comment_change_records: CommentChangeRecord

    @property
    def comment_updated(self):
        return self._comment_updates

    @property
    def comment_change_records(self):
        return self._comment_change_records

    def register_comment_create(self, comment: Comment):
        self._comment_updates = CommentUpdate(comment=comment, action=ChangeType.CREATE)

    def register_comment_update(self, comment: Comment):
        self._comment_updates = CommentUpdate(comment=comment, action=ChangeType.UPDATE)

    def register_comment_delete(self, comment: Comment):
        self._comment_updates = CommentUpdate(
            comment=comment, action=ChangeType.DISCARD
        )

    def _handle_comment_create(self, comment_update: CommentUpdate):
        self._comment_change_records = _build_comment_change(
            comment_id=comment_update.comment.comment_id,
            reason=self._reason,
            action=ChangeType.CREATE,
        )

    def _handle_comment_update(self, comment_update: CommentUpdate):
        self._comment_change_records = _build_comment_change(
            comment_id=comment_update.comment.comment_id,
            reason=self._reason,
            action=ChangeType.UPDATE,
        )

    def _handle_comment_delete(self, comment_update: CommentUpdate):
        self._comment_change_records = _build_comment_change(
            comment_id=comment_update.comment.comment_id,
            reason=self._reason,
            action=ChangeType.DISCARD,
        )

    def _handle_comment_records(self) -> None:
        handlers = {
            ChangeType.CREATE: self._handle_comment_create,
            ChangeType.UPDATE: self._handle_comment_update,
            ChangeType.DISCARD: self._handle_comment_delete,
        }
        if self._comment_updates:
            handlers[self._comment_updates.action](self._comment_updates)

    def commit(self, reason: ChangeReason) -> None:
        self._reason = reason
        logger.info("Commiting comment transaction.")
        self._handle_comment_records()
