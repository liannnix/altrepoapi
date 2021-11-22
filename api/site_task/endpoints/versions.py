from collections import namedtuple

from api.base import APIWorker
from api.misc import lut
from ..sql import sql


class PackageVersionsFromTasks(APIWorker):
    """Retrieves packages information from last tasks."""

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        self.validation_results = []

        if self.args["name"] == "":
            self.validation_results.append(f"package name should not be empty string")

        if self.args["branch"] is not None:
            if (
                self.args["branch"] == ""
                or self.args["branch"] not in lut.known_branches
            ):
                self.validation_results.append(
                    f"unknown package set name : {self.args['branch']}"
                )
                self.validation_results.append(
                    f"allowed package set names are : {lut.known_branches}"
                )

        if self.validation_results != []:
            return False
        else:
            return True

    def get(self):
        self.name = self.args["name"]
        self.branch = self.args["branch"]

        if self.branch is not None:
            branch_sub = f"WHERE task_repo = '{self.branch}'"
        else:
            self.branch = ""
            branch_sub = ""

        # get package versions from tasks
        self.conn.request_line = self.sql.get_all_src_versions_from_tasks.format(
            name=self.name, branch_sub=branch_sub
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

        PkgVersions = namedtuple(
            "PkgVersions", ["task", "hash", "branch", "owner", "changed", "name", "version", "release"]
        )
        pkg_versions = [PkgVersions(*el)._asdict() for el in response]
        pkg_versions.sort(key=lambda val: val["changed"], reverse=True)

        res = {
            "request_args": self.args,
            "length": len(pkg_versions),
            "versions": pkg_versions,
        }

        return res, 200
