from collections import namedtuple

from utils import (
    tuplelist_to_dict,
    sort_branches,
)

from api.base import APIWorker
from ..sql import sql
from ...misc import lut


class SourcePackageVersions(APIWorker):
    """Retrieves information about deleted package."""

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

        if self.validation_results != []:
            return False
        else:
            return True

    def get(self):
        self.name = self.args["name"]
        self.conn.request_line = self.sql.get_pkg_versions.format(name=self.name)
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        if not response:
            self._store_error(
                {
                    "message": f"No information found for {self.name} in DB",
                    "args": self.args,
                },
                self.ll.INFO,
                404,
            )
            return self.error
        pkg_versions = []
        PkgVersions = namedtuple(
            "PkgVersions", ["branch", "version", "release", "pkghash"]
        )
        # sort package versions by branch
        pkg_branches = sort_branches([el[0] for el in response])
        pkg_versions = tuplelist_to_dict(response, 3)
        # workaround for multiple versions of returned for certain branch
        pkg_versions = [
            PkgVersions(*(b, *pkg_versions[b][-3:]))._asdict() for b in pkg_branches
        ]

        res = {
            "request_args": self.args,
            "versions": pkg_versions,
        }

        return res, 200


class PackageVersions(APIWorker):
    """Retrieves package versions"""

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

        if self.args["package_type"] == 'binary' and self.args["arch"] is None:
            self.validation_results.append(
                f"package architecture should be specified for binary package"
            )
            self.validation_results.append(f"allowed archs are : {lut.known_archs}")

        if self.args["arch"] is not None and self.args["arch"] not in lut.known_archs:
            self.validation_results.append(
                f"unknown package arch : {self.args['arch']}"
            )
            self.validation_results.append(f"allowed archs are : {lut.known_archs}")

        if self.validation_results != []:
            return False
        else:
            return True

    def get(self):
        self.name = self.args["name"]
        self.arch = self.args['arch']
        self.pkg_type = self.args["package_type"]
        pkg_type_to_sql = {"source": 1, "binary": 0}
        source = pkg_type_to_sql[self.pkg_type]
        if source:
            self.conn.request_line = self.sql.get_pkg_versions.format(name=self.name)
        else:
            self.conn.request_line = self.sql.get_pkg_binary_versions.format(
                name=self.name, arch=self.arch
            )
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        if not response:
            self._store_error(
                {
                    "message": f"No information found for {self.name} in DB",
                    "args": self.args,
                },
                self.ll.INFO,
                404,
            )
            return self.error
        pkg_versions = []
        PkgVersions = namedtuple(
            "PkgVersions", ["branch", "version", "release", "pkghash"]
        )
        # sort package versions by branch
        pkg_branches = sort_branches([el[0] for el in response])
        pkg_versions = tuplelist_to_dict(response, 3)
        # workaround for multiple versions of returned for certain branch
        pkg_versions = [
            PkgVersions(*(b, *pkg_versions[b][-3:]))._asdict() for b in pkg_branches
        ]

        res = {
            "request_args": self.args,
            "versions": pkg_versions,
        }

        return res, 200
