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


class PackageVersionsFromImages(APIWorker):
    """Retrieves binary packages versions from images."""

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def get(self):
        name = self.args["name"]
        branch = self.args["branch"]
        edition = self.args["edition"]
        img_type = self.args["type"]
        taglike = f"{branch}:{edition}:%%:{img_type}"

        response = self.send_sql_request(
            self.sql.get_pkgs_versions_from_images.format(
                name=name,
                branch=branch,
                edition=edition,
                taglike=taglike,
                img_type=img_type,
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

        PkgVersions = namedtuple(
            "PkgVersions",
            [
                "hash",
                "name",
                "version",
                "release",
                "arch",
                "uuid",
                "tag",
                "platform",
                "variant",
                "version_major",
                "version_minor",
                "version_sub",
                "img_arch",
                "img_flavor",
                "type",
            ],
        )

        versions = [PkgVersions(*el)._asdict() for el in response]  # type: ignore
        for pkg in versions:
            pkg["hash"] = str(pkg["hash"])

        res = {
            "request_args": self.args,
            "length": len(versions),
            "versions": versions,
        }

        return res, 200
