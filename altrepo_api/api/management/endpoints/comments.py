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

from datetime import UTC, datetime
from typing import Any, Optional

from altrepo_api.api.base import APIWorker
from altrepo_api.utils import get_logger, get_real_ip, make_snowflake_id, mmhash

from .common.base import CommentListElement, UserInfo
from .common.base import ChangeReason, Comment, Reference
from .common.constants import CHANGE_ACTION_CREATE, CHANGE_ACTION_DISCARD
from .common.helpers import store_comment, store_comment_change_record
from .common.comments_transaction import Transaction
from .common.utils import validate_action, validate_comment_entity_type
from ..sql import sql


logger = get_logger(__name__)


class Comments(APIWorker):
    """
    Post, disable or enable a comment
    based on related entity link and type.
    """

    def __init__(self, connection, payload, **kwargs):
        self.payload: dict[str, Any] = payload
        self.id: Optional[str] = kwargs.get("id")
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        self.trx = Transaction()
        self.reason: ChangeReason
        self.comment: Comment
        super().__init__()

    def _check_comment_id(self, id):
        """
        Check if the comment exists in the DB.
        """
        response = self.send_sql_request(
            self.sql.check_comment_exists.format(id=int(id))
        )
        if not self.sql_status:
            return False
        return response[0][0] != 0

    def check_comment_id(self):
        return self._check_comment_id(self.id)

    def make_comment(
        self,
        pid: Optional[int],
        rid: Optional[int],
        entity_type: str,
        entity_link: str,
        author: str,
        text: str,
        references: list[Reference],
    ):
        created = datetime.now().astimezone(UTC)

        id = make_snowflake_id(
            created,
            (
                mmhash(
                    "".join(
                        (
                            entity_type,
                            entity_link,
                            author,
                            text,
                        )
                    )
                )
                + created.microsecond
            )
            & 0xFFFFFFFF,
        )

        if not pid:
            pid = id

        if not rid:
            rid = id

        self.comment = Comment(
            id,
            int(pid),
            int(rid),
            entity_type,
            entity_link,
            author,
            text,
            references,
            created,
        )

    def _validate_comment_payload(self, comment: dict[str, Any]) -> None:
        if comment == {}:
            self.validation_results.append("Comment should be specified")
            return

        pid = comment.get("pid")
        rid = comment.get("rid")
        entity_type = comment.get("entity_type")
        entity_link = comment.get("entity_link")

        if not entity_type:
            self.validation_results.append("Entity type should be specified")
            return
        elif not validate_comment_entity_type(entity_type):
            self.validation_results.append("Incorrect entity type.")
            return

        if not entity_link:
            self.validation_results.append("Entity link should be specified.")
            return

        # Case with creating a reply to existing comment (both pid and rid provided)
        if pid and rid:
            if not self._check_comment_id(pid):
                self.validation_results.append(
                    "Parent comment`s ID does not exist in DB."
                )
                return
            if not self._check_comment_id(rid):
                self.validation_results.append(
                    "Root comment`s ID does not exist in DB."
                )
                return
        # Invalid combination (only one of pid/rid provided)
        if (not rid and pid) or (rid and not pid):
            self.validation_results.append(
                "Both parent ID and root ID must be provided for replies, "
                "or neither for root comments"
            )
            return

    def _validate_payload(self):
        if not self.payload.get("user"):
            self.validation_results.append("User name should be specified")

        if not self.payload.get("reason"):
            self.validation_results.append("Reason should be specified")

        if not self.payload.get("action"):
            self.validation_results.append("Action should be specified")
        elif not validate_action(self.payload.get("action", "")):
            self.validation_results.append(
                "Comment change action '%s' is not supported"
                % self.payload.get("action")
            )

        if self.payload.get("action") == CHANGE_ACTION_CREATE:
            self._validate_comment_payload(self.payload.get("comment", {}))

    def check_payload(self) -> bool:
        """
        Check payload for create, update, discard actions.
        """
        self._validate_payload()

        if self.validation_results != []:
            return False

        self.reason = ChangeReason(
            user=UserInfo(name=self.payload["user"], ip=get_real_ip()),
            message=self.payload["reason"],
            details={},
        )

        if self.payload["action"] == CHANGE_ACTION_CREATE:
            comment = self.payload.get("comment", {})
            self.make_comment(
                # TODO: parent and root ids are not used for a now
                None,
                None,
                comment.get("entity_type"),
                comment.get("entity_link"),
                self.reason.user.name,
                comment.get("text"),
                [
                    Reference(type=r.get("type"), link=r.get("link"))
                    for r in comment.get("references", [])
                ],
            )
        else:
            response = self.send_sql_request(
                self.sql.get_comment_by_id.format(id=self.id)
            )
            if not self.sql_status or not response[0]:
                return False

            comment = response[0]
            self.comment = Comment(
                comment_id=comment[0],
                comment_pid=comment[1],
                comment_rid=comment[2],
                comment_entity_type=comment[3],
                comment_entity_link=comment[4],
                comment_author=comment[5],
                comment_text=comment[6],
                comment_references=[
                    Reference(type, link) for type, link in zip(comment[7], comment[8])
                ],
                comment_created=comment[9],
            )

        return True

    def post(self):
        """
        Create a comment related to vulnerability.
        """

        # use parent and root IDs if possible
        response = self.send_sql_request(
            self.sql.get_last_comment.format(
                entity_link=self.comment.comment_entity_link,
                entity_type=self.comment.comment_entity_type,
            )
        )
        if not self.sql_status:
            return self.error

        if response:
            self.comment = self.comment._replace(comment_pid=int(response[0][0]))
            self.comment = self.comment._replace(comment_rid=int(response[0][2]))

        self.trx.register_comment_create(self.comment)

        return self._commit_changes()

    def delete(self):
        """
        Discard a comment related to vulnerability.
        """

        self.trx.register_comment_delete(self.comment)

        return self._commit_changes()

    def put(self):
        """
        Enable discarded a comment related to vulnerability.
        """

        self.trx.register_comment_update(self.comment)

        return self._commit_changes()

    def _commit_changes(self):

        self.trx.commit(self.reason)

        if self.payload.get("action") == CHANGE_ACTION_CREATE:
            store_comment(self, self.trx.comment_updated.comment)
            if not self.sql_status:
                return self.error

        store_comment_change_record(self, self.trx.comment_change_records)
        if not self.sql_status:
            return self.error

        self.logger.info("All changes comitted to DB.")

        return {
            "request_args": self.args,
            "result": "OK",
            "comment": CommentListElement(
                self.trx.comment_updated.comment,
                self.payload.get("action") == CHANGE_ACTION_DISCARD,
            ).asdict(),
        }, 200
