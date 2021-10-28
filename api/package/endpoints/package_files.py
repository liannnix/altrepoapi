from collections import namedtuple

from database.package_sql import packagesql
from api.base import APIWorker
from utils import full_file_permissions, bytes2human


class PackageFiles(APIWorker):
    """Retrieves package files information by hash"""

    def __init__(self, connection, pkghash, **kwargs):
        self.conn = connection
        self.pkghash = pkghash
        self.args = kwargs
        self.sql = packagesql
        super().__init__()

    def get(self):
        self.conn.request_line = self.sql.get_pkg_files.format(pkghash=self.pkghash)
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        if not response:
            self._store_error(
                {
                    "message": f"No information found in DB for package hash {self.pkghash}",
                    "args": self.pkghash,
                },
                self.ll.INFO,
                404,
            )
            return self.error

        PkgFiles = namedtuple("PkgFiles",
                              ["file_name", "file_size", "file_class", "symlink", "file_mtime", "file_mode"])
        pkg_files = [PkgFiles(*el)._asdict() for el in response]

        for elem in pkg_files:
            elem["file_mode"] = full_file_permissions(elem["file_class"], elem["file_mode"])
            elem["file_size"] = bytes2human(elem["file_size"])

        res = {
            "request_args": self.pkghash,
            "length": len(pkg_files),
            "files": pkg_files
        }
        return res, 200
