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
        self.conn.request_line = self.sql.get_src_pkg_ver_rel_maintainer.format(
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
        scr_packages = response

        # create temporary table with task_id, subtask_id
        tmp_table = "tmp_repocop_src"
        self.conn.request_line = self.sql.create_tmp_table.format(
            tmp_table=tmp_table,
            columns="(rc_srcpkg_name String, rc_srcpkg_version String, rc_srcpkg_release String, pkgset_name String)",
        )
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        # insert task_id, subtask_id into temporary table
        self.conn.request_line = (
            self.sql.insert_into_tmp_table.format(tmp_table=tmp_table),
            (
                {
                    "pkgset_name": el[0],
                    "rc_srcpkg_name": el[1],
                    "rc_srcpkg_version": el[2],
                    "rc_srcpkg_release": el[3],
                }
                for el in scr_packages
            ),
        )
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error

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

        self.conn.request_line = self.sql.get_repocop_by_maintainer.format(
            tmp_table=tmp_table
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
