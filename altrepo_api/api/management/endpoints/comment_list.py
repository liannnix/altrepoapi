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

from altrepo_api.api.base import APIWorker
from altrepo_api.utils import get_logger

from .tools.utils import validate_comment_entity_type
from .tools.base import CommentListElement, Comment
from ..sql import sql


logger = get_logger(__name__)


class CommentsList(APIWorker):
    """
    Get a list of comments
    based on related entity link and type.
    """

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def check_params(self) -> bool:
        if not validate_comment_entity_type(self.args.get("entity_type", "")):
            self.validation_results.append("Incorrect entity type.")
            return False
        return super().check_params()

    def get(self):
        """
        Get a list of comments related to entity link and type.
        """
        response = self.send_sql_request(
            self.sql.get_comments_list.format(
                entity_type=self.args["entity_type"],
                entity_link=self.args["entity_link"],
            )
        )

        if not response:
            return self.store_error({"message": "No comments found"})

        if not self.sql_status:
            return {
                "message": "Failed to get comments",
                "details": "Database error occurred",
            }, 500

        comments = [
            CommentListElement(comment=Comment(*el[:-1]), is_discarded=el[-1]).asdict()
            for el in response
        ]

        return ({"length": len(comments), "comments": comments}, 200)
