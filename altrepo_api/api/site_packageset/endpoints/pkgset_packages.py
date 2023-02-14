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
from datetime import timedelta

from altrepo_api.utils import sort_branches, datetime_to_iso

from altrepo_api.api.base import APIWorker
from altrepo_api.api.misc import lut
from ..sql import sql

MAX_BRANCH_HIST_REWIND = 5


class PackagesetPackages(APIWorker):
    """Retrieves packages information in given package set."""

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        self.validation_results = []

        if self.args["group"]:
            match = False
            if self.args["group"] not in lut.pkg_groups:
                for el in lut.pkg_groups:
                    if (
                        el.startswith(self.args["group"])
                        and self.args["group"][-1] == "/"
                    ) or el.startswith(self.args["group"] + "/"):
                        match = True
                        break
            else:
                match = True
            if not match:
                self.validation_results.append(
                    f"unknown package category : {self.args['group']}"
                )
                self.validation_results.append(
                    f"allowed package categories : {lut.pkg_groups}"
                )

        if self.args["buildtime"] and self.args["buildtime"] < 0:
            self.validation_results.append(
                "package build time should be integer UNIX time representation"
            )

        if self.validation_results != []:
            return False
        else:
            return True

    def get(self):
        self.pkg_type = self.args["package_type"]
        self.branch = self.args["branch"]
        self.group = self.args["group"]
        self.buildtime = self.args["buildtime"]

        def escape_string(s: str) -> str:
            return s.replace("/", r"\/").replace("+", r"\+")

        if self.group is not None:
            # case insensitive regex matches groups and subgroups
            group = (
                r"AND match(pkg_group_, '(?i)"
                + escape_string(self.group)
                + r"(\/[\w\+\ \-]+|$)+')"
            )
        else:
            group = ""
            self.group = ""

        pkg_type_to_sql = {"source": (1,), "binary": (0,), "all": (1, 0)}
        sourcef = pkg_type_to_sql[self.pkg_type]

        response = self.send_sql_request(
            (
                self.sql.get_repo_packages.format(src=sourcef, group=group),
                {"buildtime": self.buildtime, "branch": self.branch},
            )
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {
                    "message": "No data found in database for given parameters",
                    "args": self.args,
                }
            )

        PkgMeta = namedtuple(
            "PkgMeta",
            [
                "hash",
                "name",
                "version",
                "release",
                "buildtime",
                "summary",
                "maintainer",
                "category",
                "changelog",
            ],
        )

        retval = [PkgMeta(*el)._asdict() for el in response]

        response = self.send_sql_request(
            (
                self.sql.get_group_subgroups.format(src=sourcef, group=self.group),
                {"branch": self.branch},
            )
        )
        if not self.sql_status:
            return self.error

        subcategories = []

        if response:
            subcategories = [el[0] for el in response]

        res = {
            "request_args": self.args,
            "length": len(retval),
            "subcategories": subcategories,
            "packages": retval,
        }

        return res, 200


class AllPackagesetsByHash(APIWorker):
    """Gets all package sets information which include given package hash."""

    def __init__(self, connection, pkghash, **kwargs):
        self.pkghash = pkghash
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def get(self):
        response = self.send_sql_request(
            self.sql.get_all_pkgsets_by_hash.format(pkghash=self.pkghash)
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {"message": "No data not found in database", "args": self.args}
            )

        res = sort_branches([el[0] for el in response])

        res = {"pkghash": str(self.pkghash), "length": len(res), "branches": res}

        return res, 200


class LastBranchPackages(APIWorker):
    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        self.validation_results = []

        if self.args["packages_limit"] < 1:
            self.validation_results.append(
                "last packages limit should be greater or equal to 1"
            )

        if self.validation_results != []:
            return False
        else:
            return True

    def get(self):
        self.branch = self.args["branch"]
        self.packager = self.args["packager"]
        self.packages_limit = self.args["packages_limit"]

        if self.packager is not None:
            packager_sub = f"AND pkg_packager_email LIKE '{self.packager}@%'"
        else:
            self.packager = ""
            packager_sub = ""

        # get last branch date
        response = self.send_sql_request(
            self.sql.get_last_branch_date.format(branch=self.branch)
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {
                    "message": "No data found in database for given parameters",
                    "args": self.args,
                }
            )

        last_branch_date = response[0][0]  # type: ignore

        if self.packager:
            tmp_table = self.sql.get_last_branch_hsh_source.format(branch=self.branch)
        else:
            # get source packages diff from current branch state and previous one
            tmp_table = "tmp_srcpkg_hashes"

            _ = self.send_sql_request(
                self.sql.get_last_branch_src_diff.format(
                    tmp_table=tmp_table,
                    branch=self.branch,
                    last_pkgset_date=last_branch_date,
                )
            )
            if not self.sql_status:
                return self.error

            # check if we have source packages diff from previous branch state
            response = self.send_sql_request(
                self.sql.check_tmp_table_count.format(tmp_table=tmp_table)
            )
            if not self.sql_status:
                return self.error

            src_diff_count = response[0][0]  # type: ignore
            t_date = last_branch_date

            if src_diff_count == 0:
                # try to go back in branch history
                for _ in range(MAX_BRANCH_HIST_REWIND):
                    # decrement date
                    t_date = t_date - timedelta(days=1)  # type: ignore

                    # drop temporary table
                    _ = self.send_sql_request(
                        self.sql.drop_tmp_table.format(tmp_table=tmp_table)
                    )
                    if not self.sql_status:
                        return self.error

                    # fill it again using new date
                    _ = self.send_sql_request(
                        self.sql.get_last_branch_src_diff.format(
                            tmp_table=tmp_table,
                            branch=self.branch,
                            last_pkgset_date=t_date,
                        )
                    )
                    if not self.sql_status:
                        return self.error

                    # check if we have source packages diff from previous branch state
                    response = self.send_sql_request(
                        self.sql.check_tmp_table_count.format(tmp_table=tmp_table)
                    )
                    if not self.sql_status:
                        return self.error

                    src_diff_count = response[0][0]  # type: ignore
                    if src_diff_count != 0:
                        break

            if src_diff_count == 0:
                return self.store_error(
                    {
                        "message": "Failed to get branch state diff from database",
                        "args": self.args,
                    }
                )

        # get source and binary packages info by hashes from temporary table
        response = self.send_sql_request(
            self.sql.get_last_branch_pkgs_info.format(
                branch=self.branch,
                hsh_source=tmp_table,
                packager=packager_sub,
                limit=self.packages_limit,
            )
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {
                    "message": "No data found in database for packages",
                    "args": self.args,
                }
            )

        PkgMeta = namedtuple(
            "PkgMeta",
            [
                "pkg_name",
                "pkg_version",
                "pkg_release",
                "pkg_summary",
                "changelog_name",
                "changelog_nickname",
                "changelog_date",
                "changelog_text",
                "hash",
                "pkg_buildtime",
            ],
        )

        last_branch_date = datetime_to_iso(last_branch_date)  # type: ignore

        retval = []

        for pkg in (PkgMeta(*el[1:])._asdict() for el in response):
            pkg["changelog_date"] = datetime_to_iso(pkg["changelog_date"])
            retval.append(pkg)

        res = {
            "request_args": self.args,
            "length": len(retval),
            "packages": retval,
            "last_branch_date": last_branch_date,
        }

        return res, 200
