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

from .base import _pAPIWorker
from ..base import CommentChangeRecord, Comment


def store_comment(cls: _pAPIWorker, comment: Comment) -> None:
    cls.status = False

    _ = cls.send_sql_request(
        (
            cls.sql.store_comment,
            [
                {
                    "comment_id": comment.comment_id,
                    "comment_pid": comment.comment_pid,
                    "comment_rid": comment.comment_rid,
                    "comment_entity_type": comment.comment_entity_type,
                    "comment_entity_link": comment.comment_entity_link,
                    "comment_author": comment.comment_author,
                    "comment_text": comment.comment_text,
                    "comment_references.type": [
                        ref.type for ref in comment.comment_references
                    ],
                    "comment_references.link": [
                        ref.link for ref in comment.comment_references
                    ],
                    "comment_created": comment.comment_created,
                }
            ],
        )
    )
    if not cls.sql_status:
        return None

    cls.status = True


def store_comment_change_record(
    cls: _pAPIWorker, comment_change_record: CommentChangeRecord
) -> None:

    cls.status = False

    _ = cls.send_sql_request(
        (
            cls.sql.store_comment_change_history,
            [comment_change_record.asdict()],
        )
    )
    if not cls.sql_status:
        return None

    cls.status = True
