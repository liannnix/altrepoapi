from api.base import APIWorker
from api.misc import lut
from ..sql import sql
from api.package.endpoints.build_dependency_set import BuildDependencySet


class TaskBuildDependencySet(APIWorker):
    """Retrieves task packages build dependencies."""

    def __init__(self, connection, id, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        self.task_id = id
        super().__init__()

    def check_task_id(self):
        self.conn.request_line = self.sql.check_task.format(id=self.task_id)

        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return False

        if response[0][0] == 0:
            return False
        return True

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        self.validation_results = []

        if self.args["archs"]:
            for arch in self.args["archs"]:
                if arch not in lut.known_archs:
                    self.validation_results.append(f"unknown package arch : {arch}")

        if self.validation_results != []:
            return False
        else:
            return True

    def get(self):
        # arguments processing
        if self.args["archs"] is None:
            self.args["archs"] = ["x86_64"]
        self.args["packages"] = []
        self.args["branch"] = None
        # get task source packages and branch
        # get task repo
        self.conn.request_line = self.sql.task_repo.format(id=self.task_id)
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        if not response:
            self._store_error(
                {"message": f"No data found in database for task '{self.task_id}'"},
                self.ll.INFO,
                404,
            )
            return self.error

        self.args["branch"] = response[0][0]
        # get task source packages
        self.conn.request_line = self.sql.task_src_packages.format(id=self.task_id)
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        if not response:
            self._store_error(
                {"message": f"No packages found in database for task '{self.task_id}'"},
                self.ll.INFO,
                404,
            )
            return self.error
        self.args["packages"] = [pkg[0] for pkg in response]
        # init BuildDependency class with args
        self.bds = BuildDependencySet(
            self.conn, self.args["packages"], self.args["branch"], self.args["archs"]
        )
        # build result
        self.bds.build_dependency_set()
        # format result
        if self.bds.status:
            # result processing
            res = {
                "id": self.task_id,
                "request_args": self.args,
                "length": len(self.bds.result),
                "packages": self.bds.result,
            }
            return res, 200
        else:
            return self.bds.error
