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

from collections import namedtuple

from altrepo_api.api.base import APIWorker
from ..sql import sql


class Bugzilla(APIWorker):
    """Retrieves information about Bugzilla registered bugs from database."""

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        return True

    def get_bug_by_package(self):
        package_name = self.args["package_name"]
        self.pkg_type = self.args["package_type"]
        pkg_type_to_sql = {"source": 1, "binary": 0}
        source = pkg_type_to_sql[self.pkg_type]

        if source == 1:
            response = self.send_sql_request(
                (
                    self.sql.get_pkg_name_by_srcpkg,
                    {"srcpkg_name": package_name},
                )
            )
            if not self.sql_status:
                return self.error
            if not response or response[0][0] == []:  # type: ignore
                return self.store_error(
                    {
                        "message": f"No data found in database for {package_name} source package",
                        "args": self.args,
                    }
                )
            packages = {el[0] for el in response}
            packages.add(package_name)
        else:
            packages = {package_name}
        response = self.send_sql_request(
            self.sql.get_bugzilla_info_by_srcpkg.format(packages=tuple(packages))
        )
        if not self.sql_status:
            return self.error
        if not response or response[0][0] == []:  # type: ignore
            return self.store_error(
                {
                    "message": f"No data found in database for packages: {packages}",
                    "args": self.args,
                }
            )

        BugzillaInfo = namedtuple(
            "BugzillaInfoModel",
            [
                "id",
                "status",
                "resolution",
                "severity",
                "product",
                "component",
                "assignee",
                "reporter",
                "summary",
                "last_changed",
            ],
        )

        res = [BugzillaInfo(*el)._asdict() for el in response]
        res = {"request_args": self.args, "length": len(res), "bugs": res}

        return res, 200

    def get_bug_by_maintainer(self):
        maintainer_nickname = self.args["maintainer_nickname"]
        by_acl = self.args["by_acl"]
        request_line = ""
        order_g = ""

        if by_acl == "by_nick":
            request_line = self.sql.get_bugzilla_info_by_nick_acl.format(
                maintainer_nickname=maintainer_nickname
            )
        if by_acl == "by_nick_leader":
            order_g = "AND order_g = 0"
            request_line = self.sql.get_bugzilla_info_by_last_acl_with_group.format(
                maintainer_nickname=maintainer_nickname, order_g=order_g
            )
        if by_acl == "by_nick_or_group":
            request_line = self.sql.get_bugzilla_info_by_nick_or_group_acl.format(
                maintainer_nickname=maintainer_nickname
            )
        if by_acl == "by_nick_leader_and_group":
            request_line = self.sql.get_bugzilla_info_by_last_acl_with_group.format(
                maintainer_nickname=maintainer_nickname, order_g=order_g
            )
        if by_acl == "none":
            request_line = self.sql.get_bugzilla_info_by_maintainer.format(
                maintainer_nickname=maintainer_nickname
            )

        response = self.send_sql_request(request_line)
        if not self.sql_status:
            return self.error
        if not response or response[0][0] == []:  # type: ignore
            return self.store_error(
                {
                    "message": f"No data found in database for {maintainer_nickname}",
                    "args": self.args,
                }
            )

        BugzillaInfo = namedtuple(
            "BugzillaInfoModel",
            [
                "id",
                "status",
                "resolution",
                "severity",
                "product",
                "component",
                "assignee",
                "reporter",
                "summary",
                "last_changed",
                "source_package_name",
                "binary_package_name",
            ],
        )
        res = [BugzillaInfo(*el)._asdict() for el in response]
        res = {"request_args": self.args, "length": len(res), "bugs": res}

        return res, 200

    def get_bugs_by_image_edition(self):
        """Get bugs filed for edition"""
        branch = self.args["branch"]
        edition = self.args["edition"]

        response = self.send_sql_request(
            self.sql.get_bugzilla_info_by_image_edition.format(
                branch=branch, edition=edition
            )
        )
        if not self.sql_status:
            return self.error
        if not response or response[0][0] == []:
            return self.store_error(
                {
                    "message": f"No data found in database for edition: {edition}",
                    "args": self.args,
                }
            )

        BugzillaInfo = namedtuple(
            "BugzillaInfoModel",
            [
                "id",
                "status",
                "resolution",
                "severity",
                "product",
                "version",
                "platform",
                "component",
                "assignee",
                "reporter",
                "summary",
                "last_changed",
            ],
        )

        res = [BugzillaInfo(*el)._asdict() for el in response]
        res = {"request_args": self.args, "length": len(res), "bugs": res}

        return res, 200
