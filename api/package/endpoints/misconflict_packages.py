# altrepodb API
# Copyright (C) 2021  BaseALT Ltd

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

from utils import get_logger, tuplelist_to_dict, remove_duplicate

from api.base import APIWorker
from api.misc import lut
from ..sql import sql
from libs.conflict_filter import ConflictFilter
from libs.exceptions import SqlRequestError


class MisconflictPackages(APIWorker):
    """Retrieves packages file conflicts."""

    def __init__(self, connection, packages, branch, archs, **kwargs) -> None:
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        self.packages = packages
        self.branch = branch
        self.archs = archs
        self.result = {}
        super().__init__()

    def find_conflicts(self, pkg_hashes: tuple[int] = None, task_repo_hashes: tuple[int] = None):
        # do all kind of black magic here
        self.packages = tuple(self.packages)
        if self.archs:
            if "noarch" not in self.archs:
                self.archs.append("noarch")
        else:
            self.archs = lut.default_archs
        self.archs = tuple(self.archs)

        if not pkg_hashes:
            # get hash for package names
            self.conn.request_line = (
                self.sql.misconflict_get_hshs_by_pkgs,
                {"pkgs": self.packages, "branch": self.branch, "arch": self.archs},
            )
            status, response = self.conn.send_request()
            if status is False:
                self._store_sql_error(response, self.ll.ERROR, 500)
                return
            if not response:
                self._store_error(
                    {
                        "message": (
                            f"Packages {list(self.packages)} not in package set '{self.branch}'"
                            f" for archs {list(self.archs)}"
                        )
                    },
                    self.ll.INFO,
                    404,
                )
                return

            # check the existence of a package by comparing the number of input
            # and selected from database
            # form a list of package hashes
            input_pkg_hshs = tuple({pkg[0] for pkg in response})
            input_pkgs_names = {pkg[1] for pkg in response}
            if len(input_pkgs_names) != len(self.packages):
                # return utils.json_str_error("Error of input data.")
                self._store_error(
                    {
                        "message": (
                            f"Packages ({set(self.packages) - input_pkgs_names}) not in"
                            f" package set '{self.branch}'"
                            f" for archs {list(self.archs)}"
                        )
                    },
                    self.ll.INFO,
                    404,
                )
                return
        else:
            input_pkg_hshs = tuple(pkg_hashes)

        # create temporary table with repository state hashes
        tmp_repo_state = "tmp_repo_state_hshs"
        self.conn.request_line = self.sql.create_tmp_table.format(
            tmp_table=tmp_repo_state, columns="(pkg_hash UInt64)"
        )
        status, response = self.conn.send_request()
        if status is False:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return
        if task_repo_hashes is not None:
            # use repository hashes from task
            self.conn.request_line = (
                self.sql.insert_into_tmp_table.format(
                    tmp_table=tmp_repo_state
                ),
                ((hsh,) for hsh in task_repo_hashes)
            )
            status, response = self.conn.send_request()
            if status is False:
                self._store_sql_error(response, self.ll.ERROR, 500)
                return
        else:
            # fill it from last_packages
            self.conn.request_line = self.sql.insert_last_packages_hashes.format(
                tmp_table=tmp_repo_state, branch=self.branch
            )
            status, response = self.conn.send_request()
            if status is False:
                self._store_sql_error(response, self.ll.ERROR, 500)
                return
        # delete unused binary packages arch hashes and '*-debuginfo' package hashes
        tmp_repo_state_filtered = "tmp_repo_state_hshs_filtered"
        self.conn.request_line = self.sql.create_tmp_table.format(
            tmp_table=tmp_repo_state_filtered, columns="(pkg_hash UInt64)"
        )
        status, response = self.conn.send_request()
        if status is False:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return
        # insert source packages hashes
        self.conn.request_line = self.sql.insert_pkgs_hshs_filtered_src.format(
            tmp_table=tmp_repo_state_filtered,
            tmp_table2=tmp_repo_state
        )
        status, response = self.conn.send_request()
        if status is False:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return
        # insert binary packages hashes
        self.conn.request_line = self.sql.insert_pkgs_hshs_filtered_bin.format(
            tmp_table=tmp_repo_state_filtered,
            tmp_table2=tmp_repo_state,
            arch=tuple(self.archs)
        )
        status, response = self.conn.send_request()
        if status is False:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return
        # drop initial repo state hashes temporary table
        self.conn.request_line = self.sql.drop_tmp_table.format(
            tmp_table=tmp_repo_state
        )
        status, response = self.conn.send_request()
        if status is False:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return
        tmp_repo_state = tmp_repo_state_filtered

        # get list of (input package | conflict package | conflict files)
        self.conn.request_line = self.sql.misconflict_get_pkgs_with_conflict.format(
            tmp_table=tmp_repo_state, hshs=input_pkg_hshs
        )
        status, response = self.conn.send_request()
        if status is False:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return
        if not response:
            # no conflict found
            self.status = True
            return
        # replace 'file_hashname' by 'fn_name' from FileNames
        hshs_files = response
        # 1. collect all files_hashnames
        f_hashnames = set()
        for el in hshs_files:
            [f_hashnames.add(x) for x in el[2]]
        # 2. select real file names from DB
        self.conn.request_line = (
            self.sql.misconflict_get_fnames_by_fnhashs,
            {"hshs": tuple(f_hashnames)},
        )
        status, response = self.conn.send_request()
        if status is False:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.result
        if not response:
            self._store_error(
                {"message": f"Failed to get file names from database by hash"},
                self.ll.INFO,
                500,
            )
            return

        f_hashnames = {}
        for r in response:
            f_hashnames[r[0]] = r[1]
        # 3. replace hashes by names in result
        new_hshs_files = []
        for el in hshs_files:
            new_hshs_files.append((*el[:2], [f_hashnames[x] for x in el[2]], *el[3:]))
        hshs_files = new_hshs_files

        # list of conflicting package pairs
        in_confl_hshs = [(hsh[0], hsh[1]) for hsh in hshs_files]

        # filter conflicts by provides/conflicts
        c_filter = ConflictFilter(self.conn, self.branch, self.archs, self.DEBUG)

        # check for the presence of the specified conflict each pair
        # if the conflict between the packages in the pair is specified,
        # then add the pair to the list
        try:
            filter_ls = c_filter.detect_conflict(in_confl_hshs)
        except SqlRequestError as e:
            self._store_error(
                {
                    "message": f"Error occured in ConflictFilter",
                    "error": e.error_details,
                },
                self.ll.ERROR,
                500,
            )
            return

        # create dict with package names by hashes
        hsh_name_dict = defaultdict(dict)
        for hsh_1, hsh_2, _, name_2, name_1, _ in hshs_files:
            hsh_name_dict[hsh_1], hsh_name_dict[hsh_2] = name_1, name_2

        # convert the hashes into names, put in the first place in the pair
        # the name of the input package, if it is not
        filter_ls_names = []
        for hsh in filter_ls:
            inp_pkg = hsh[0] if hsh[0] in input_pkg_hshs else hsh[1]
            out_pkg = hsh[0] if hsh[0] != inp_pkg else hsh[1]
            result_pair = (hsh_name_dict[inp_pkg], hsh_name_dict[out_pkg])
            if result_pair not in filter_ls:
                filter_ls_names.append(result_pair)

        # form the list of tuples (input package | conflict package | conflict files)
        result_list, output_pkgs = [], set()
        for pkg in hshs_files:
            [output_pkgs.add(i) for i in pkg[:2]]
            pkg = (hsh_name_dict[pkg[0]], hsh_name_dict[pkg[1]], pkg[2])
            if pkg not in result_list:
                result_list.append(pkg)

        # get architectures of found packages
        self.conn.request_line = self.sql.misconflict_get_pkg_archs.format(
            hshs=tuple(output_pkgs)
        )
        status, response = self.conn.send_request()
        if status is False:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return

        pkg_archs_dict = tuplelist_to_dict(response, 1)

        # look for duplicate pairs of packages in the list with different files
        # and join them
        result_dict_cleanup = defaultdict(list)
        for pkg in result_list:
            result_dict_cleanup[(pkg[0], pkg[1])] += pkg[2]

        confl_pkgs = remove_duplicate([pkg[1] for pkg in result_dict_cleanup.keys()])

        # get main information of packages by package hashes
        self.conn.request_line = self.sql.misconflict_get_meta_by_hshs.format(
            tmp_table=tmp_repo_state, pkgs=tuple(confl_pkgs)
        )
        status, response = self.conn.send_request()
        if status is False:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return

        # form dict name - package info
        name_info_dict = {}
        for pkg in response:
            name_info_dict[pkg[0]] = pkg[1:]

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
        self.validation_results = []
        if self.args["branch"] not in lut.known_branches:
            self.validation_results.append(
                f"unknown package set name : {self.args['branch']}"
            )
            self.validation_results.append(
                f"allowed package set names are : {lut.known_branches}"
            )

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
