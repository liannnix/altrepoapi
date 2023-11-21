# ALTRepo API
# Copyright (C) 2021-2023  BaseALT Ltd

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from collections import namedtuple

from altrepo_api.api.base import APIWorker
from altrepo_api.utils import full_file_permissions
from ..sql import sql


class FileSearch(APIWorker):
    """
    File search by name or directory.
    """

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        self.validation_results = []

        if self.args["limit"] and self.args["limit"] < 1:
            self.validation_results.append("limit should be greater or equal to 1")

        if self.validation_results != []:
            return False
        return True

    def get(self):
        input_val = self.args["file_name"].replace("_", r"\_")
        branch = self.args["branch"]
        files_limit = self.args["limit"]

        if files_limit:
            limit_clause = f"LIMIT {files_limit}"
        else:
            limit_clause = ""

        find_files = self.send_sql_request(
            self.sql.find_files.format(
                branch=branch, input=input_val, limit=limit_clause
            )
        )
        if not self.sql_status:
            return self.error
        if not find_files:
            return self.store_error(
                {"message": "No data not found in database"},
            )

        _tmp_table = "tmp_file_search"

        response = self.send_sql_request(
            self.sql.get_files_info.format(tmp_table=_tmp_table),
            external_tables=[
                {
                    "name": _tmp_table,
                    "structure": [
                        ("fn_name", "String"),
                        ("pkg_hash", "UInt64"),
                    ],
                    "data": find_files,
                }
            ],
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {"message": "No data not found in database"},
            )

        FileSearchMeta = namedtuple(
            "FileSearch",
            [
                "file_name",
                "file_hashname",
                "file_class",
                "symlink",
                "file_mode",
            ],
        )

        res = sorted(
            (FileSearchMeta(*el)._asdict() for el in response),
            key=lambda k: (len(k["file_name"]), k["file_name"]),
        )

        for elem in res:
            elem["file_mode"] = full_file_permissions(
                elem["file_class"], elem["file_mode"]
            )

        res = {"request_args": self.args, "length": len(res), "files": res}
        return res, 200


class FastFileSearchLookup(APIWorker):
    """
    Fast search files by name or directory.
    """

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        self.validation_results = []

        if self.args["limit"] and self.args["limit"] < 1:
            self.validation_results.append("limit should be greater or equal to 1")

        if self.validation_results != []:
            return False
        return True

    def get(self):
        input_val = self.args["file_name"].replace("_", r"\_")
        branch = self.args["branch"]
        files_limit = self.args["limit"]

        if files_limit:
            # FIXME: extend limit here to get more relevant results due to
            # sorting implemented on API side to decrease SQL request time
            limit_clause = f"LIMIT {files_limit * 4}"
        else:
            limit_clause = ""

        response = self.send_sql_request(
            self.sql.fast_find_files.format(
                branch=branch, input=input_val, limit=limit_clause
            )
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {"message": "No data not found in database"},
            )

        files = [
            {"file_name": f}
            for f in sorted((el[0] for el in response), key=lambda k: (len(k), k))
        ]
        # XXX: apply actual limit value to results here
        if files_limit:
            files = files[:files_limit]
        res = {"request_args": self.args, "length": len(files), "files": files}
        return res, 200
