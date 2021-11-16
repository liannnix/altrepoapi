from collections import namedtuple

from api.base import APIWorker
from api.misc import lut
from ..sql import sql


class BinaryPackageLog(APIWorker):
    """Gets a link to the binary package build log"""

    def __init__(self, connection, pkghash, **kwargs):
        self.pkghash = pkghash
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def get(self):
        self.conn.request_line = self.sql.get_bin_pkg_log.format(pkghash=self.pkghash)
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        if not response:
            self._store_error(
                {"message": f"No data not found in database for {self.pkghash}"},
                self.ll.INFO,
                404,
            )
            return self.error

        BuildLog = namedtuple(
            "BuildLog",
            [
                "task_id",
                "subtask_id",
                "subtask_arch",
                "buildlog_hash",
            ],
        )

        res = BuildLog(*response[0])
        return {
            "pkg_hash": str(self.pkghash),
            "task_id": res.task_id,
            "subtask_id": res.subtask_id,
            "subtask_arch": res.subtask_arch,
            "buildlog_hash": str(res.buildlog_hash),
            "link": f"{lut.gitalt_base}/tasks/{str(res.task_id)}/build/{str(res.subtask_id)}/{res.subtask_arch}/log"
        }, 200
