from collections import namedtuple

from utils import sort_branches

from api.base import APIWorker
from api.misc import lut
from ..sql import sql


class MaintainerBranches(APIWorker):
    """Retrieves maintainer's packages summary by branches from last package sets."""

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        self.validation_results = []

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
        self.conn.request_line = self.sql.get_maintainer_branches.format(
            maintainer_nickname=maintainer_nickname
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

        MaintainerBranches = namedtuple("MaintainerBranches", ["branch", "count"])
        branches = []
        for branch in sort_branches([el[0] for el in response]):
            for el in [MaintainerBranches(*b)._asdict() for b in response]:
                if el["branch"] == branch:
                    branches.append(el)
                    break
        res = {"request_args": self.args, "length": len(branches), "branches": branches}

        return res, 200
