# ALTRepo API
# Copyright (C) 2021-2024  BaseALT Ltd

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

from collections import namedtuple

from altrepo_api.api.base import APIWorker
from ..sql import sql


class FindImagesByPackageName(APIWorker):
    """
    Search for images by package name.
    """

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def get(self):
        branch = self.args["branch"]
        edition = self.args["edition"]
        pkg_name = self.args["pkg_name"]
        img_show = self.args["img_show"]
        pkg_type = self.args["pkg_type"]

        if branch:
            branch_clause = f"AND img_branch = '{branch}'"
        else:
            branch_clause = ""

        if edition:
            edition_clause = f"AND img_edition = '{edition}'"
        else:
            edition_clause = ""

        if img_show == "active":
            img_show_clause = """
            AND img_tag IN (
            SELECT img_tag
            FROM (
                  SELECT img_tag,
                         argMax(img_show, ts) AS img_show
                  FROM ImageTagStatus
                  GROUP BY img_tag
            ) WHERE img_show = 'show'
            )
            """
        else:
            img_show_clause = ""

        if pkg_type == "binary":
            pkg_type_clause = """
            WHERE pkg_name = '{pkg_name}'
                AND pkg_sourcepackage = 0
            """.format(
                pkg_name=pkg_name
            )
        else:
            pkg_type_clause = """
            WHERE pkg_srcrpm_hash IN (
                SELECT pkg_hash
                FROM Packages
                WHERE pkg_name = '{pkg_name}'
                  AND pkg_sourcepackage = 1
            )
              AND (pkg_sourcepackage = 0)
            """.format(
                pkg_name=pkg_name
            )

        response = self.send_sql_request(
            self.sql.get_find_imgs_by_pkg_name.format(
                branch=branch_clause,
                pkg_type=pkg_type_clause,
                img_show=img_show_clause,
                edition=edition_clause,
            )
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {
                    "message": "No data found in database",
                    "args": self.args,
                }
            )

        FindImgsMeta = namedtuple(
            "FindImgsMeta",
            [
                "pkghash",
                "name",
                "branch",
                "version",
                "release",
                "arch",
                "edition",
                "tag",
                "file",
                "date",
            ],
        )

        images = [FindImgsMeta(*el)._asdict() for el in response]  # type: ignore

        res = {
            "request_args": self.args,
            "length": len(images),
            "images": images,
        }
        return res, 200
