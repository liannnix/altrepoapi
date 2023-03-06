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

from collections import namedtuple

from altrepo_api.utils import datetime_to_iso

from altrepo_api.api.base import APIWorker
from altrepo_api.api.misc import lut
from ..sql import sql


class RepologyExport(APIWorker):
    """Retrieves package info from DB."""

    def __init__(self, connection, branch, **kwargs):
        self.branch = branch
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        self.validation_results = []

        if self.branch == "" or self.branch not in lut.repology_export_branches:
            self.validation_results.append(f"unknown package set name : {self.branch}")
            self.validation_results.append(
                f"allowed package set names are : {lut.repology_export_branches}"
            )

        if self.validation_results != []:
            return False
        else:
            return True

    def get(self):
        # get branch stat
        response = self.send_sql_request(
            self.sql.get_branch_stat.format(branch=self.branch)
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {
                    "message": f"No data found for branch '{self.branch}'",
                    "args": self.args,
                }
            )

        RepoStat = namedtuple("RepoStat", ["arch", "cnt"])
        repo_date, repo_stat = response[0][0], [  # type: ignore
            RepoStat(*el)._asdict() for el in response[0][1]  # type: ignore
        ]

        # get package info
        response = self.send_sql_request(
            self.sql.get_branch_pkg_info.format(branch=self.branch)
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {
                    "message": f"No data found for branch '{self.branch}'",
                    "args": self.args,
                }
            )

        SrcPkgInfo = namedtuple(
            "SrcPkgInfo",
            [
                "name",
                "epoch",
                "version",
                "release",
                "category",
                "url",
                "summary",
                "license",
                "packager",
                "recipe",
                "binaries",
            ],
        )
        BinPkgInfo = namedtuple(
            "BinPkgInfo", ["name", "epoch", "version", "release", "summary", "archs"]
        )
        src_packages = [SrcPkgInfo(*el)._asdict() for el in response]

        # build result packages dictionary
        for src in src_packages:
            src["binaries"] = sorted(
                [BinPkgInfo(*el)._asdict() for el in src["binaries"]],
                key=lambda x: x["name"],
            )
            src["homepage"] = f'{lut.packages_base}/{self.branch}/srpms/{src["name"]}/'
            _specfile = src["recipe"]
            src[
                "recipe"
            ] = f'{lut.packages_base}/{self.branch}/srpms/{src["name"]}/specfiles/'
            src[
                "recipe_raw"
            ] = f'{lut.packages_base}/{self.branch}/srpms/{src["name"]}/specfiles/{_specfile}'
            src["CPE"] = ""  # TODO: add CPE info for packages when ready
            src[
                "bugzilla"
            ] = f'{lut.bugzilla_base}/buglist.cgi?quicksearch={src["name"]}'

        res = {
            "branch": self.branch,
            "date": datetime_to_iso(repo_date),  # type: ignore
            "stats": repo_stat,
            "packages": src_packages,
        }

        return res, 200
