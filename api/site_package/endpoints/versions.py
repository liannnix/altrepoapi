from collections import namedtuple

from utils import (
    tuplelist_to_dict,
    sort_branches,
)

from api.base import APIWorker
from ..sql import sql


class SourcePackageVersions(APIWorker):
    """Get source package versions from last package sets."""

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
