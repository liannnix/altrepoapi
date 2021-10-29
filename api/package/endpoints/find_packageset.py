from collections import namedtuple

from api.base import APIWorker
from api.misc import lut
from ..sql import sql


class FindPackageset(APIWorker):
    """Retrieves binary packages in package sets by source packages."""
    
    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        self.validation_results = []

        if self.args["branches"]:
            for br in self.args["branches"]:
                if br not in lut.known_branches:
                    self.validation_results.append(f"unknown package set name : {br}")
                    self.validation_results.append(
                        f"allowed package set names are : {lut.known_branches}"
                    )
                    break

        for pkg in self.args["packages"]:
            if pkg == "":
                self.validation_results.append(
                    "package list from argument should not contain empty values"
                )
                break

        if self.validation_results != []:
            return False
        else:
            return True

    def get(self):
        self.packages = tuple(self.args["packages"])
        if self.args["branches"]:
            branchs_cond = f"AND pkgset_name IN {tuple(self.args['branches'])}"
        else:
            branchs_cond = ""

        self.conn.request_line = (
            self.sql.get_branch_with_pkgs.format(branchs=branchs_cond),
            {"pkgs": self.packages},
        )
        status, response = self.conn.send_request()
        if status is False:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error

        if not response:
            self._store_error(
                {
                    "message": f"No results found in last package sets for given parameters",
                    "args": self.args,
                },
                self.ll.INFO,
                404,
            )
            return self.error

        PkgsetInfo = namedtuple(
            "PkgsetInfo",
            [
                "branch",
                "sourcepkgname",
                "pkgset_datetime",
                "packages",
                "version",
                "release",
                "disttag",
                "packager_email",
                "buildtime",
                "archs",
            ],
        )

        res = [PkgsetInfo(*el)._asdict() for el in response]

        res = {"request_args": self.args, "length": len(res), "packages": res}

        return res, 200
