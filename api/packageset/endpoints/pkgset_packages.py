from collections import namedtuple

from api.base import APIWorker
from api.misc import lut
from ..sql import sql


class PackagesetPackages(APIWorker):
    """Retrieves package set packages information."""
    
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

        if self.args["package_type"] not in ("source", "binary", "all"):
            self.validation_results.append(
                f"package type should be one of 'source', 'binary' or 'all' not '{self.args['package_type']}'"
            )

        if self.args["archs"]:
            for arch in self.args["archs"]:
                if arch not in lut.known_archs:
                    self.validation_results.append(f"unknown package arch : {arch}")

        if self.validation_results != []:
            return False
        else:
            return True

    def get(self):
        self.pkg_type = self.args["package_type"]
        self.branch = self.args["branch"]
        self.archs = self.args["archs"]
        if self.archs:
            if "noarch" not in self.archs:
                self.archs = self.archs.append("noarch")
        else:
            self.archs = lut.known_archs
        self.archs = tuple(self.archs)

        depends_type_to_sql = {"source": (1,), "binary": (0,), "all": (1, 0)}
        sourcef = depends_type_to_sql[self.pkg_type]

        self.conn.request_line = self.sql.get_repo_packages.format(
            branch=self.branch, archs=self.archs, src=sourcef
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

        PkgMeta = namedtuple(
            "PkgMeta",
            [
                "name",
                "version",
                "release",
                "summary",
                "maintainers",
                "url",
                "license",
                "category",
                "archs",
                "acl_list",
            ],
        )

        retval = [PkgMeta(*el)._asdict() for el in response]

        res = {"request_args": self.args, "length": len(retval), "packages": retval}
        return res, 200
