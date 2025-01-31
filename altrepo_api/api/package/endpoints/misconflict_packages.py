# ALTRepo API
# Copyright (C) 2021-2025  BaseALT Ltd

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

from collections import defaultdict, namedtuple
from typing import Iterable, Optional

from altrepo_api.utils import (
    get_logger,
    tuplelist_to_dict,
    remove_duplicate,
    make_tmp_table_name,
)

from altrepo_api.api.base import APIWorker
from altrepo_api.api.misc import lut
from ..sql import sql
from altrepo_api.libs.conflict_filter import ConflictFilter
from altrepo_api.libs.exceptions import SqlRequestError


class MisconflictPackages(APIWorker):
    """Retrieves packages file conflicts."""

    def __init__(
        self,
        connection,
        packages: tuple[str],
        branch: str,
        archs: Optional[Iterable[str]],
        **kwargs,
    ) -> None:
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        self.packages = packages
        self.branch = branch
        self.archs = list(archs) if archs else []
        self.result = []
        super().__init__()

    def find_conflicts(
        self,
        pkg_hashes: Optional[tuple[int, ...]] = None,
        task_repo_hashes: Optional[tuple[int, ...]] = None,
    ):
        # do all kind of black magic here
        self.packages = self.packages
        if self.archs and "noarch" not in self.archs:
            self.archs.append("noarch")
        else:
            self.archs = lut.default_archs

        if not pkg_hashes:
            # get hash for package names
            response = self.send_sql_request(
                (
                    self.sql.misconflict_get_hshs_by_pkgs,
                    {"pkgs": self.packages, "branch": self.branch, "arch": self.archs},
                )
            )
            if not self.sql_status:
                return
            if not response:
                _ = self.store_error(
                    {
                        "message": (
                            f"Packages {self.packages} not in package set '{self.branch}'"
                            f" for archs {self.archs}"
                        )
                    }
                )
                return

            # check the existence of a package by comparing the number of input
            # and selected from database
            # form a list of package hashes
            input_pkg_hshs = tuple({pkg[0] for pkg in response})
            input_pkgs_names = {pkg[1] for pkg in response}
            if len(input_pkgs_names) != len(self.packages):
                # return utils.json_str_error("Error of input data.")
                _ = self.store_error(
                    {
                        "message": (
                            f"Packages ({set(self.packages) - input_pkgs_names}) not in"
                            f" package set '{self.branch}'"
                            f" for archs {self.archs}"
                        )
                    }
                )
                return
        else:
            input_pkg_hshs = tuple(pkg_hashes)

        # store input_pkg_hashes to temporary table
        tmp_pkg_hshs = make_tmp_table_name("input_pkg_hshs")

        _ = self.send_sql_request(
            self.sql.create_tmp_table.format(
                tmp_table=tmp_pkg_hshs, columns="(pkg_hash UInt64)"
            )
        )
        if not self.sql_status:
            return

        _ = self.send_sql_request(
            (
                self.sql.insert_into_tmp_table.format(tmp_table=tmp_pkg_hshs),
                ((hsh,) for hsh in input_pkg_hshs),
            )
        )
        if not self.sql_status:
            return

        # create temporary table with repository state hashes
        tmp_repo_state = make_tmp_table_name("repo_state_hshs")

        _ = self.send_sql_request(
            self.sql.create_tmp_table.format(
                tmp_table=tmp_repo_state, columns="(pkg_hash UInt64)"
            )
        )
        if not self.sql_status:
            return

        if task_repo_hashes is not None:
            # use repository hashes from task
            _ = self.send_sql_request(
                (
                    self.sql.insert_into_tmp_table.format(tmp_table=tmp_repo_state),
                    ((hsh,) for hsh in task_repo_hashes),
                )
            )
            if not self.sql_status:
                return
        else:
            # fill it from last_packages
            _ = self.send_sql_request(
                self.sql.insert_last_packages_hashes.format(
                    tmp_table=tmp_repo_state, branch=self.branch
                )
            )
            if not self.sql_status:
                return
        # delete unused binary packages arch hashes and '*-debuginfo' package hashes
        tmp_repo_state_filtered = make_tmp_table_name("repo_state_hshs_filtered")

        _ = self.send_sql_request(
            self.sql.create_tmp_table.format(
                tmp_table=tmp_repo_state_filtered, columns="(pkg_hash UInt64)"
            )
        )
        if not self.sql_status:
            return
        # insert source packages hashes
        _ = self.send_sql_request(
            self.sql.insert_pkgs_hshs_filtered_src.format(
                tmp_table=tmp_repo_state_filtered, tmp_table2=tmp_repo_state
            )
        )
        if not self.sql_status:
            return
        # insert binary packages hashes
        _ = self.send_sql_request(
            self.sql.insert_pkgs_hshs_filtered_bin.format(
                tmp_table=tmp_repo_state_filtered,
                tmp_table2=tmp_repo_state,
                arch=tuple(self.archs),
            )
        )
        if not self.sql_status:
            return
        # drop initial repo state hashes temporary table
        _ = self.send_sql_request(
            self.sql.drop_tmp_table.format(tmp_table=tmp_repo_state)
        )
        if not self.sql_status:
            return

        tmp_repo_state = tmp_repo_state_filtered

        # get list of (input package | conflict package | conflict files)
        response = self.send_sql_request(
            self.sql.misconflict_get_pkgs_with_conflict.format(
                tmp_table=tmp_repo_state, tmp_table2=tmp_pkg_hshs
            )
        )
        if not self.sql_status:
            return
        if not response:
            # no conflict found
            self.status = True
            return

        # replace 'file_hashname' by 'fn_name' from FileNames
        ConflicFiles = namedtuple(
            "ConflicFiles",
            ["in_pkg_hash", "c_pkg_hash", "fn_hashes", "c_pkg_name", "in_pkg_name"],
        )

        conflict_pkgs_files = [ConflicFiles(*el[:-1]) for el in response]

        # drop input package hashes temporary table
        _ = self.send_sql_request(
            self.sql.drop_tmp_table.format(tmp_table=tmp_pkg_hshs)
        )
        if not self.sql_status:
            return

        # check whether files has the same md5, mode, mtime and class
        # and exclude such conflicts like the `apt` and `rpm` does
        _tmp_table = make_tmp_table_name("file_conflicts")
        response = self.send_sql_request(
            self.sql.misconflict_check_file_conflicts.format(tmp_table=_tmp_table),
            external_tables=[
                {
                    "name": _tmp_table,
                    "structure": [
                        ("in_pkg_hash", "UInt64"),
                        ("c_pkg_hash", "UInt64"),
                        ("fn_hash", "UInt64"),
                    ],
                    "data": [
                        {
                            "in_pkg_hash": c.in_pkg_hash,
                            "c_pkg_hash": c.c_pkg_hash,
                            "fn_hash": f_hsh,
                        }
                        for c in conflict_pkgs_files
                        for f_hsh in c.fn_hashes
                    ],
                }
            ],
        )
        if not self.sql_status:
            return self.result
        if not response:
            _ = self.store_error(
                {"message": "Failed to get file names from database by hash"},
                self.LL.ERROR,
                500,
            )
            return

        EqualFile = namedtuple("EqualFile", ["in_pkg_hahs", "c_pkg_hash", "fn_hash"])

        equal_conflict_files = {EqualFile(*el[:-1]) for el in response if el[-1] == 1}

        # filter out files conflicts
        for c in conflict_pkgs_files[:]:
            if all(
                [
                    (c.in_pkg_hash, c.c_pkg_hash, h) in equal_conflict_files
                    for h in c.fn_hashes
                ]
            ):
                # all files are equal -> remove conflict element
                conflict_pkgs_files.remove(c)
            elif any(
                [
                    (c.in_pkg_hash, c.c_pkg_hash, h) in equal_conflict_files
                    for h in c.fn_hashes
                ]
            ):
                # some of file conflicts are not equal -> filtering files list
                conflict_pkgs_files.remove(c)
                conflict_pkgs_files.append(
                    ConflicFiles(
                        c.in_pkg_hash,
                        c.c_pkg_hash,
                        [
                            h
                            for h in c.fn_hashes
                            if (c.in_pkg_hash, c.c_pkg_hash, h)
                            not in equal_conflict_files
                        ],
                        c.in_pkg_name,
                        c.c_pkg_name,
                    )
                )

        # if all file conflicts are resolved return then
        if not conflict_pkgs_files:
            self.status = True
            return

        # 1. collect all files_hashnames
        f_hashnames = {h for c in conflict_pkgs_files for h in c.fn_hashes}

        # 2. select real file names from DB
        # use external table to do not exceed `max query size` limit
        _tmp_table = make_tmp_table_name("file_name_hashes")
        response = self.send_sql_request(
            self.sql.misconflict_get_fnames_by_fnhashs.format(tmp_table=_tmp_table),
            external_tables=[
                {
                    "name": _tmp_table,
                    "structure": [("fn_hash", "UInt64")],
                    "data": [{"fn_hash": h} for h in f_hashnames],
                }
            ],
        )
        if not self.sql_status:
            return self.result
        if not response:
            _ = self.store_error(
                {"message": "Failed to get file names from database by hash"},
                self.LL.ERROR,
                500,
            )
            return

        file_names = {el[0]: el[1] for el in response}

        # 3. replace hashes by names in result
        ConflicFilesNames = namedtuple(
            "ConflicFilesNames",
            ["c_pkg_hash", "in_pkg_hash", "file_names", "c_pkg_name", "in_pkg_name"],
        )

        conflict_pkgs_files = [
            ConflicFilesNames(
                c.c_pkg_hash,
                c.in_pkg_hash,
                [file_names[h] for h in c.fn_hashes],
                c.c_pkg_name,
                c.in_pkg_name,
            )
            for c in conflict_pkgs_files
        ]

        # create dict with package names by hashes
        hsh_name_dict = defaultdict(dict)
        for c in conflict_pkgs_files:
            hsh_name_dict[c.c_pkg_hash] = c.c_pkg_name
            hsh_name_dict[c.in_pkg_hash] = c.in_pkg_name

        # list of conflicting package pairs
        in_confl_hshs = [(c.c_pkg_hash, c.in_pkg_hash) for c in conflict_pkgs_files]

        # filter conflicts by provides/conflicts
        c_filter = ConflictFilter(self.conn, self.DEBUG)

        # check for the presence of the specified conflict each pair
        # if the conflict between the packages in the pair is specified,
        # then add the pair to the list
        try:
            filter_ls = c_filter.detect_conflict(in_confl_hshs)
        except SqlRequestError as e:
            _ = self.store_error(
                {
                    "message": "Error occured in ConflictFilter",
                    "error": e.error_details,
                },
                self.LL.ERROR,
                500,
            )
            return

        # convert the hashes into names, put in the first place in the pair
        # the name of the input package, if it is not there
        filter_ls_names = set()
        for hsh in filter_ls:
            inp_pkg = hsh[0] if hsh[0] in input_pkg_hshs else hsh[1]
            out_pkg = hsh[0] if hsh[0] != inp_pkg else hsh[1]
            filter_ls_names.add((hsh_name_dict[inp_pkg], hsh_name_dict[out_pkg]))

        # build the list of tuples (input package | conflict package | conflict files)
        intermediate_results, output_pkgs_hashes = set(), set()
        for c in conflict_pkgs_files:
            output_pkgs_hashes.update((c.c_pkg_hash, c.in_pkg_hash))
            intermediate_results.add((c.in_pkg_name, c.c_pkg_name, tuple(c.file_names)))

        # get architectures of found packages
        response = self.send_sql_request(
            self.sql.misconflict_get_pkg_archs.format(hshs=tuple(output_pkgs_hashes))
        )
        if not self.sql_status:
            return

        pkg_archs_dict = tuplelist_to_dict(response, 1)  # type: ignore

        # look for duplicate pairs of packages in the list with different files
        # and join them
        result_dict_cleanup = defaultdict(list)
        for pkg in intermediate_results:
            result_dict_cleanup[(pkg[0], pkg[1])] += pkg[2]

        confl_pkgs = remove_duplicate([pkg[1] for pkg in result_dict_cleanup.keys()])

        # get main information of packages by package hashes
        response = self.send_sql_request(
            self.sql.misconflict_get_meta_by_hshs.format(
                tmp_table=tmp_repo_state, pkgs=tuple(confl_pkgs)
            )
        )
        if not self.sql_status:
            return

        # form dict name - package info
        name_info_dict = {el[0]: el[1:] for el in response}

        # form list of tuples (input pkg | conflict pkg | pkg info | conflict files)
        # and filter it
        result_list_info = []
        for pkg, files in result_dict_cleanup.items():
            inp_pkg_archs = set(pkg_archs_dict[pkg[0]])
            found_pkg_archs = set(pkg_archs_dict[pkg[1]])
            intersect_pkg_archs = inp_pkg_archs.intersection(found_pkg_archs)

            if (pkg[0], pkg[1]) not in filter_ls_names and intersect_pkg_archs:
                pkg = (
                    (pkg[0], pkg[1])
                    + name_info_dict[pkg[1]][:-1]
                    + (list(intersect_pkg_archs),)
                    + (files,)
                )
                result_list_info.append(pkg)

        # magic ends here
        ConflictPackages = namedtuple(
            "ConflictPackages",
            [
                "input_package",
                "conflict_package",
                "version",
                "release",
                "epoch",
                "archs",
                "files_with_conflict",
            ],
        )

        self.result = [ConflictPackages(*el)._asdict() for el in result_list_info]
        self.status = True


class PackageMisconflictPackages:
    """Retrieves file conflicts by packages."""

    def __init__(self, connection, **kwargs) -> None:
        self.conn = connection
        self.args = kwargs
        self.validation_results = None
        self.logger = get_logger(__name__)

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        return True

    def get(self):
        # arguments processing
        pass
        # init BuildDependency class with args
        mp = MisconflictPackages(
            self.conn,
            self.args["packages"],
            self.args["branch"].lower(),
            self.args["archs"],
        )

        # build result
        mp.find_conflicts()

        # format result
        if mp.status:
            # result processing
            res = {
                "request_args": self.args,
                "length": len(mp.result),
                "conflicts": mp.result,
            }
            return res, 200
        else:
            return mp.error
