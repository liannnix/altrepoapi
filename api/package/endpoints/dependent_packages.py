from collections import namedtuple

from api.base import APIWorker
from api.misc import lut
from database.package_sql import packagesql


class DependentPackages(APIWorker):
    """Retrieves dependent packages."""

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = packagesql
        super().__init__()

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        self.validation_results = []

        if self.args["name"] == "":
            self.validation_results.append("file name not specified")

        if self.args["branch"] == "" or self.args["branch"] not in lut.known_branches:
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
        self.package = self.args["name"]
        self.branch = self.args["branch"]

        self.conn.request_line = self.sql.get_dependent_packages.format(
            package=self.package, branch=self.branch
        )
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        if not response:
            self._store_error(
                {
                    "message": f"No data found in database for given parameters",
                    "args": self.args,
                },
                self.ll.INFO,
                404,
            )
            return self.error

        PkgInfo = namedtuple(
            "PkgInfo",
            [
                "name",
                "version",
                "release",
                "epoch",
                "serial",
                "sourcerpm",
                "branch",
                "archs",
            ],
        )

        retval = [PkgInfo(*el)._asdict() for el in response]

        res = {"request_args": self.args, "length": len(retval), "packages": retval}
        return res, 200
