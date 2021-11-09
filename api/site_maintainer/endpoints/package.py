from collections import namedtuple

from api.base import APIWorker
from api.misc import lut
from ..sql import sql


class MaintainerPackages(APIWorker):
    """Retrieves maintainer's packages information from last package sets."""

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
        self.conn.request_line = self.sql.get_maintainer_pkg.format(
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

        MaintainerPackages = namedtuple(
            "MaintainerPackagesModel",
            ["name", "buildtime", "url", "summary", "version", "release"],
        )
        res = [MaintainerPackages(*el)._asdict() for el in response]
        res = {"request_args": self.args, "length": len(res), "packages": res}

        return res, 200
