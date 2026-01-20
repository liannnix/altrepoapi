# ALTRepo API
# Copyright (C) 2021-2026  BaseALT Ltd

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

from altrepo_api.utils import datetime_to_iso

from altrepo_api.api.base import APIWorker
from ..sql import sql


class LastPackagesWithCVEFix(APIWorker):
    """Retrieves information about last packages with CVE's in changelog."""

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        return True

    def get(self):
        self.branch = self.args["branch"]

        response = self.send_sql_request(
            self.sql.get_last_packages_with_cve_fixes.format(branch=self.branch)
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {
                    "message": f"No packages with recent CVE fixes from {self.branch} found",
                    "args": self.args,
                }
            )

        PackageMeta = namedtuple(
            "PackageMeta",
            [
                "name",
                "version",
                "release",
                "buildtime",
                "summary",
                "changelog_date",
                "changelog_text",
            ],
        )

        packages = [
            dict(hash=str(el[0]), **PackageMeta(*el[1:])._asdict()) for el in response
        ]
        for package in packages:
            package["changelog_date"] = datetime_to_iso(package["changelog_date"])  # type: ignore

        res = {"request_args": self.args, "length": len(packages), "packages": packages}

        return res, 200
