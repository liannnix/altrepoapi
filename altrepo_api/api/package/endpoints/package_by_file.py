# ALTRepo API
# Copyright (C) 2021-2024  BaseALT Ltd

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

from typing import NamedTuple

from altrepo_api.utils import tuplelist_to_dict, make_tmp_table_name

from altrepo_api.api.base import APIWorker
from altrepo_api.api.misc import lut
from altrepo_api.api.parser import file_name_wc_type
from ..sql import sql


class PkgInfo(NamedTuple):
    pkgcs: str
    name: str
    sourcepackage: str
    version: str
    release: str
    disttag: str
    arch: str
    branch: str
    files: list[str]


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
        # escape `%` sign
        self.file = self.file.replace("%", "\\%")
        # replacae wildcards '*' with SQL-like '%'
        self.file = self.file.replace("*", "%")
        self.arch = self.args["arch"]
        self.branch = self.args["branch"]
        if self.arch:
            self.arch = (self.arch, "noarch")
        else:
            self.arch = lut.known_archs
        self.arch = tuple(self.arch)

        # if file:
        tmp_file_names = make_tmp_table_name("file_names_hash")
        _ = self.send_sql_request(
            (
                self.sql.gen_table_fnhshs_by_file.format(tmp_table=tmp_file_names),
                {"elem": self.file},
            )
        )
        if not self.sql_status:
            return self.error

        return self._find_packages(tmp_file_names)

    def check_params_post(self):
        self.validation_results = []

        self.files: list[str] = []
        for file in self.args["json_data"]["files"]:
            try:
                file = file_name_wc_type(file)
            except ValueError as e:
                self.validation_results.append(str(e))
            else:
                if "*" in file:
                    self.validation_results.append(
                        "Invalid file name: {0}. wildcard symbols are not allowed".format(
                            file
                        )
                    )
                self.files.append(file)

        self.branch = self.args["json_data"]["branch"]
        if self.branch not in lut.known_branches:
            self.validation_results.append(
                "Invalid branch name: {0}".format(self.branch)
            )

        self.arch = self.args["json_data"].get("arch")
        if self.arch:
            if self.arch not in lut.known_archs:
                self.validation_results.append(
                    "Invalid architecture name: {0}".format(self.arch)
                )
            else:
                self.arch = (self.arch, "noarch")
        else:
            self.arch = lut.known_archs

        return self.validation_results == []

    def post(self):
        self.arch = tuple(self.arch)

        tmp_file_names = make_tmp_table_name("file_names")
        _ext_filenames = make_tmp_table_name("ext_filenames")

        _ = self.send_sql_request(
            self.sql.gen_table_fnhsh_by_files.format(
                tmp_table=tmp_file_names, ext_table=_ext_filenames
            ),
            external_tables=[
                {
                    "name": _ext_filenames,
                    "structure": [("fn_name", "String")],
                    "data": [{"fn_name": file} for file in self.files],
                }
            ],
        )
        if not self.sql_status:
            return self.error

        return self._find_packages(tmp_file_names)

    def _find_packages(self, tmp_file_names: str):
        response = self.send_sql_request(
            self.sql.select_all_tmp_table.format(tmp_table=tmp_file_names)
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

        file_names: dict[int, str] = dict()
        for f in response:
            file_names[f[0]] = f[1]

        tmp_files = make_tmp_table_name("files")
        _ = self.send_sql_request(
            (
                self.sql.gen_table_hshs_by_file.format(
                    tmp_table=tmp_files,
                    param=self.sql.gen_table_hshs_by_file_mod_hashname.format(
                        tmp_table=tmp_file_names
                    ),
                ),
                {"branch": self.branch, "arch": self.arch},
            )
        )
        if not self.sql_status:
            return self.error

        response = self.send_sql_request(
            self.sql.select_all_tmp_table.format(tmp_table=tmp_files)
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

        ids_filename_dict: dict[str, list[str]] = {}

        for k, v in tuplelist_to_dict(response, 1).items():
            ids_filename_dict[k] = [file_names[x] for x in v]

        response = self.send_sql_request(
            (
                self.sql.pkg_by_file_get_meta_by_hshs.format(tmp_table=tmp_files),
                {"branch": self.branch},
            )
        )
        if not self.sql_status:
            return self.error

        packages: list[PkgInfo] = []
        for package in response:
            package += (ids_filename_dict[package[0]],)
            packages.append(PkgInfo(*package[1:]))

        not_found = []
        # get file name or file names count to include in response JSON
        _files = ""
        if hasattr(self, "file"):
            _files = self.file
        if hasattr(self, "files"):
            _files = len(self.files)
            not_found = list(
                set(self.files) - set(f for p in packages for f in p.files)
            )

        res = {
            "request_args": {"branch": self.branch, "arch": self.arch, "files": _files},
            "length": len(packages),
            "packages": [p._asdict() for p in packages],
            "not_found": not_found,
        }
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

        tmp_files = make_tmp_table_name("files")
        _ = self.send_sql_request(
            (
                self.sql.gen_table_hshs_by_file.format(
                    tmp_table=tmp_files, param=self.sql.gen_table_hshs_by_file_mod_md5
                ),
                {"branch": self.branch, "arch": self.arch, "elem": self.md5},
            )
        )
        if not self.sql_status:
            return self.error

        response = self.send_sql_request(
            self.sql.select_all_tmp_table.format(tmp_table=tmp_files)
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
            self.sql.pkg_by_file_get_fnames_by_fnhashs.format(tmp_table=tmp_files)
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
                self.sql.pkg_by_file_get_meta_by_hshs.format(tmp_table=tmp_files),
                {"branch": self.branch},
            )
        )
        if not self.sql_status:
            return self.error

        output_values = []
        for package in response:  # type: ignore
            package += (ids_filename_dict[package[0]],)  # type: ignore
            output_values.append(package[1:])

        res = [PkgInfo(*el)._asdict() for el in output_values]

        res = {"request_args": self.args, "length": len(res), "packages": res}
        return res, 200
