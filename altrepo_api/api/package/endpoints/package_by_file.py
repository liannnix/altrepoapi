# ALTRepo API
# Copyright (C) 2021-2022  BaseALT Ltd

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

from altrepo_api.utils import tuplelist_to_dict

from altrepo_api.api.base import APIWorker
from altrepo_api.api.misc import lut
from ..sql import sql


class PackageByFileName(APIWorker):
    """Retrieves package information by file name."""

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        return True

    def get(self):
        self.file = self.args["file"]
        # replacae wildcards '*' with SQL-like '%'
        self.file = self.file.replace("*", "%")
        self.arch = self.args["arch"]
        self.branch = self.args["branch"]
        if self.arch:
            self.arch = (self.arch, "noarch")
        else:
            self.arch = lut.known_archs
        self.arch = tuple(self.arch)

        file_names = {}
        # if file:
        _ = self.send_sql_request(
            (
                self.sql.gen_table_fnhshs_by_file.format(tmp_table="TmpFileNames"),
                {"elem": self.file},
            )
        )
        if not self.sql_status:
            return self.error

        response = self.send_sql_request(
            self.sql.select_all_tmp_table.format(tmp_table="TmpFileNames")
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {
                    "message": "No data found in database for given parameters",
                    "args": self.args,
                }
            )

        for f in response:
            file_names[f[0]] = f[1]

        _ = self.send_sql_request(
            (
                self.sql.gen_table_hshs_by_file.format(
                    tmp_table="TmpFiles",
                    param=self.sql.gen_table_hshs_by_file_mod_hashname.format(
                        tmp_table="TmpFileNames"
                    ),
                ),
                {"branch": self.branch, "arch": self.arch},
            )
        )
        if not self.sql_status:
            return self.error

        response = self.send_sql_request(
            self.sql.select_all_tmp_table.format(tmp_table="TmpFiles")
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {
                    "message": "No data found in database for given parameters",
                    "args": self.args,
                }
            )

        ids_filename_dict = tuplelist_to_dict(response, 1)  # type: ignore

        new_ids_filename_dict = {}

        for k, v in ids_filename_dict.items():
            new_ids_filename_dict[k] = [file_names[x] for x in v]

        ids_filename_dict = new_ids_filename_dict

        response = self.send_sql_request(
            (
                self.sql.pkg_by_file_get_meta_by_hshs.format(tmp_table="TmpFiles"),
                {"branch": self.branch},
            )
        )
        if not self.sql_status:
            return self.error

        output_values = []
        for package in response:  # type: ignore
            package += (ids_filename_dict[package[0]],)  # type: ignore
            output_values.append(package[1:])

        PkgInfo = namedtuple(
            "PkgInfo",
            [
                "pkgcs",
                "name",
                "sourcepackage",
                "version",
                "release",
                "disttag",
                "arch",
                "branch",
                "files",
            ],
        )

        retval = [PkgInfo(*el)._asdict() for el in output_values]

        res = {"request_args": self.args, "length": len(retval), "packages": retval}
        return res, 200


class PackageByFileMD5(APIWorker):
    """Retrieves package information by file MD5 checksum."""

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        return True

    def get(self):
        self.md5 = self.args["md5"]
        self.arch = self.args["arch"]
        self.branch = self.args["branch"]
        if self.arch:
            if "noarch" not in self.arch:
                self.arch = (self.arch, "noarch")
        else:
            self.arch = lut.known_archs
        self.arch = tuple(self.arch)

        _ = self.send_sql_request(
            (
                self.sql.gen_table_hshs_by_file.format(
                    tmp_table="TmpFiles", param=self.sql.gen_table_hshs_by_file_mod_md5
                ),
                {"branch": self.branch, "arch": self.arch, "elem": self.md5},
            )
        )
        if not self.sql_status:
            return self.error

        response = self.send_sql_request(
            self.sql.select_all_tmp_table.format(tmp_table="TmpFiles")
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {
                    "message": "No data found in database for given parameters",
                    "args": self.args,
                }
            )

        ids_filename_dict = tuplelist_to_dict(response, 1)  # type: ignore

        file_names = {}
        # 1. collect all files_hashname
        f_hashnames = set()
        for v in ids_filename_dict.values():
            [f_hashnames.add(x) for x in v]
        # 2. select real file names from DB
        response = self.send_sql_request(
            self.sql.pkg_by_file_get_fnames_by_fnhashs.format(tmp_table="TmpFiles")
        )
        if not self.sql_status:
            return self.error

        if not response:
            return self.store_error(
                {
                    "message": "No data found in database for given parameters",
                    "args": self.args,
                }
            )

        for r in response:
            file_names[r[0]] = r[1]

        new_ids_filename_dict = {}

        for k, v in ids_filename_dict.items():
            new_ids_filename_dict[k] = [file_names[x] for x in v]

        ids_filename_dict = new_ids_filename_dict

        response = self.send_sql_request(
            (
                self.sql.pkg_by_file_get_meta_by_hshs.format(tmp_table="TmpFiles"),
                {"branch": self.branch},
            )
        )
        if not self.sql_status:
            return self.error

        output_values = []
        for package in response:  # type: ignore
            package += (ids_filename_dict[package[0]],)  # type: ignore
            output_values.append(package[1:])

        PkgInfo = namedtuple(
            "PkgInfo",
            [
                "pkgcs",
                "name",
                "sourcepackage",
                "version",
                "release",
                "disttag",
                "arch",
                "branch",
                "files",
            ],
        )

        res = [PkgInfo(*el)._asdict() for el in output_values]

        res = {"request_args": self.args, "length": len(res), "packages": res}
        return res, 200
