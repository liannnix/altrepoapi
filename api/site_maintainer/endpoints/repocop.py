from collections import namedtuple

from api.base import APIWorker
from api.misc import lut
from ..sql import sql


class RepocopByMaintainer(APIWorker):
    """Retrieves Repocop test results for maintainer's packages."""

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        self.validation_results = []

        if self.args["branch"] == "" or self.args["branch"] not in lut.known_branches:
            self.validation_results.append(
                f"unknown package set name : {self.args['branch']}"
            )
            self.validation_results.append(
                f"allowed package set names are : {lut.known_branches}"
            )

        if self.args["maintainer_nickname"] == "":
            self.validation_results.append(
                f"maintainer nickname should not be empty string"
            )

        if self.validation_results != []:
            return False
        else:
            return True

    def get(self):
        maintainer_nickname = self.args["maintainer_nickname"]
        branch = self.args["branch"]
        order_g = ""

        MaintainerRepocop = namedtuple(
            "MaintainerRepocop",
            [
                "pkg_name",
                "pkg_version",
                "pkg_release",
                "pkg_arch",
                "srcpkg_name",
                "branch",
                "test_name",
                "test_status",
                "test_message",
                "test_date",
            ],
        )

        if self.args['by_acl'] == 'by_nick_leader_and_group':
            self.conn.request_line = self.sql.get_repocop_by_last_acl_with_group.format(
                maintainer_nickname=maintainer_nickname, branch=branch, order_g=order_g
            )
        if self.args['by_acl'] == 'by_nick_leader':
            order_g = "AND order_g=0"
            self.conn.request_line = self.sql.get_repocop_by_last_acl_with_group.format(
                maintainer_nickname=maintainer_nickname, branch=branch, order_g=order_g
            )
        if self.args['by_acl'] == 'by_nick':
            self.conn.request_line = self.sql.get_repocop_by_nick_acl.format(
                maintainer_nickname=maintainer_nickname, branch=branch
            )
        if self.args['by_acl'] == 'by_nick_or_group':
            self.conn.request_line = self.sql.get_repocop_by_nick_or_group_acl.format(
                maintainer_nickname=maintainer_nickname, branch=branch
            )
        if self.args['by_acl'] == 'none':
            self.conn.request_line = self.sql.get_maintainer_repocop.format(
                maintainer_nickname=maintainer_nickname, branch=branch
            )
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        if not response:
            self._store_error(
                {"message": f"No data not found in database", "args": self.args},
                self.ll.INFO,
                404,
            )
            return self.error
        res = [MaintainerRepocop(*el)._asdict() for el in response]

        res = {"request_args": self.args, "length": len(res), "packages": res}

        return res, 200
