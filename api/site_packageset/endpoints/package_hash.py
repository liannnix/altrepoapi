from api.base import APIWorker
from api.misc import lut
from ..sql import sql


class PackagesetPackageHash(APIWorker):
    """Retrieves package hash by package name in package set."""

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

        if self.args["name"] == "":
            self.validation_results.append(f"package name should not be empty string")

        if self.validation_results != []:
            return False
        else:
            return True

    def get(self):
        self.branch = self.args["branch"]
        self.name = self.args["name"]

        self.conn.request_line = self.sql.get_pkghash_by_name.format(
            branch=self.branch, name=self.name
        )
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        if not response:
            self._store_error(
                {
                    "message": f"Package '{self.name}' not found in package set '{self.branch}'",
                    "args": self.args,
                },
                self.ll.INFO,
                404,
            )
            return self.error

        res = {
            "request_args": self.args,
            "pkghash": str(response[0][0]),
            "version": response[0][1],
            "release": response[0][2],
        }
        return res, 200


class PackagesetPackageBinaryHash(APIWorker):
    """Retrieves package hash by package binary name in package set."""

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

        if self.args["arch"] == "" or self.args["arch"] not in lut.known_archs:
            self.validation_results.append(
                f"unknown package set name : {self.args['branch']}"
            )
            self.validation_results.append(
                f"allowed package set names are : {lut.known_branches}"
            )

        if self.args["name"] == "":
            self.validation_results.append(f"package name should not be empty string")

        if self.validation_results != []:
            return False
        else:
            return True

    def get(self):
        self.branch = self.args["branch"]
        self.arch = self.args["arch"]
        self.name = self.args["name"]

        self.conn.request_line = self.sql.get_pkghash_by_binary_name.format(
            branch=self.branch, arch=self.arch, name=self.name
        )
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        if not response:
            self._store_error(
                {
                    "message": f"Package '{self.name}' architecture {self.arch} not found in package set '{self.branch}'",
                    "args": self.args,
                },
                self.ll.INFO,
                404,
            )
            return self.error

        res = {
            "request_args": self.args,
            "pkghash": str(response[0][0]),
            "version": response[0][1],
            "release": response[0][2],
        }
        return res, 200
