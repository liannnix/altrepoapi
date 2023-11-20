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
from typing import Optional

from altrepo_api.settings import namespace as settings
from altrepo_api.utils import (
    get_logger,
    tuplelist_to_dict,
    join_tuples,
    make_tmp_table_name,
)
from altrepo_api.api.misc import lut
from altrepo_api.api.base import APIWorker
from altrepo_api.libs.dependency_sorting import SortList
from altrepo_api.api.task.endpoints.task_repo import LastRepoStateFromTask

from ..sql import sql


class BuildDependency(APIWorker):
    """Retrieves packages build dependencies."""

    def __init__(
        self,
        connection,
        packages,
        branch,
        archs,
        leaf,
        depth,
        dptype,
        filterbybin,
        filterbysrc,
        finitepkg,
        oneandhalf=False,
        **kwargs,
    ):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        self.packages = packages
        self.branch = branch
        self.arch = archs
        self.leaf = leaf
        self.depth = depth
        self.dptype = dptype
        self.reqfilter = filterbybin
        self.reqfiltersrc = filterbysrc
        self.finitepkg = finitepkg
        self.oneandhalf = oneandhalf
        self.result = {}
        super().__init__()

    def build_dependencies(self, task_repo_hashes: Optional[tuple[int, ...]] = None):
        # do all kind of black magic here
        input_pkgs = self.packages
        depends_type_to_sql = {"source": (1,), "binary": (0,), "both": (1, 0)}
        sourcef = depends_type_to_sql[self.dptype]

        if self.arch:
            # always add 'noarch' if not specified
            if "noarch" not in self.arch:
                self.arch.append("noarch")
        else:
            # get default archs for given branch
            self.arch = (
                lut.branch_wds_default_archs.get(self.branch)
                or lut.branch_wds_default_archs["default"]
            )

        # store source packages by level
        # store source packages level 0
        src_pkgs_by_level = {0: tuple(input_pkgs)}

        def store_src_pkgs_levels(levels_dict: dict, tmp_table: str) -> bool:
            """Select and store packages from temporary table splitted by dependecy levels.

            Args:
                levels_dict (dict): packages dictionary (key: depth level (0..n), val: packages tuple)

            Returns:
                bool: False - if error ocured during SQL request
            """

            response = self.send_sql_request(
                self.sql.select_all_tmp_table.format(tmp_table=tmp_table)
            )
            if not self.sql_status:
                return False

            pkgs = [el[0] for el in response]  # type: ignore
            pkgs_prev_level = []
            for p in levels_dict.values():
                pkgs_prev_level += p
            levels_dict[max(levels_dict.keys()) + 1] = tuple(
                [pkg for pkg in pkgs if pkg not in pkgs_prev_level]
            )
            return True

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
                arch=tuple(self.arch),
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

        # create shadow copy for last_depends and last_packages_with_source
        # proceed with last_packages_with_source
        # 1. create shadowing temporary table
        _ = self.send_sql_request(self.sql.create_shadow_last_pkgs_w_srcs)
        if not self.sql_status:
            return

        # 2. fill shadowing temporary table
        _ = self.send_sql_request(
            self.sql.fill_shadow_last_pkgs_w_srcs.format(
                tmp_table=tmp_repo_state, branch=self.branch
            )
        )
        if not self.sql_status:
            return

        # proceed with last_depends
        # 1. create shdowing temporary table
        _ = self.send_sql_request(self.sql.create_shadow_last_depends)
        if not self.sql_status:
            return

        # 2. fill shadowing temporary table
        _ = self.send_sql_request(
            self.sql.fill_shadow_last_depends.format(
                tmp_table=tmp_repo_state, branch=self.branch
            )
        )
        if not self.sql_status:
            return

        # create tmp table with list of packages
        tmp_pkgs_list = make_tmp_table_name("packages_list")

        _ = self.send_sql_request(
            self.sql.create_tmp_table.format(
                tmp_table=tmp_pkgs_list, columns="(pkgname String)"
            )
        )
        if not self.sql_status:
            return

        # base query - first iteration, build requires depth 1
        _ = self.send_sql_request(
            (
                self.sql.insert_build_req_deep_1.format(tmp_table=tmp_pkgs_list),
                {
                    "sfilter": sourcef,
                    "pkgs": input_pkgs,
                    "branch": self.branch,
                    "archs": tuple(self.arch),
                    "union": list(input_pkgs),
                },
            )
        )
        if not self.sql_status:
            return

        # store source packages level 1
        if not store_src_pkgs_levels(src_pkgs_by_level, tmp_pkgs_list):
            return

        #  set depth to 2 if in 'oneandhalf' mode
        if self.oneandhalf:
            self.depth = 2

        if self.depth > 1:
            # sql wrapper for increase depth
            deep_wrapper = self.sql.increase_depth_wrap.format(tmp_table=tmp_pkgs_list)

            # process depth for every level and add results to `package_list`
            for _ in range(self.depth - 1):
                _ = self.send_sql_request(
                    (
                        self.sql.insert_result_for_depth_level.format(
                            wrapper=deep_wrapper, tmp_table=tmp_pkgs_list
                        ),
                        {
                            "sfilter": sourcef,
                            "branch": self.branch,
                            "archs": tuple(self.arch),
                        },
                    )
                )
                if not self.sql_status:
                    return
                # store source packages level 2..n
                if not store_src_pkgs_levels(src_pkgs_by_level, tmp_pkgs_list):
                    return

        # if 'oneandhalf' is set search dependencies of level 1 source packages from level 2 binary packages
        # filter level 2 packages from which level1 packages are depends
        if self.oneandhalf:
            # create and fill temporary tables for source packages filtering
            tmp_l1_pkgs = make_tmp_table_name("l1_pkgs")
            tmp_l2_pkgs = make_tmp_table_name("l2_pkgs")
            # level 1 packages
            _ = self.send_sql_request(
                self.sql.create_tmp_table.format(
                    tmp_table=tmp_l1_pkgs, columns="(pkgname String)"
                )
            )
            if not self.sql_status:
                return

            _ = self.send_sql_request(
                (
                    self.sql.insert_into_tmp_table.format(tmp_table=tmp_l1_pkgs),
                    ((pkg,) for pkg in src_pkgs_by_level[1]),
                )
            )
            if not self.sql_status:
                return

            # level 2 packages
            _ = self.send_sql_request(
                self.sql.create_tmp_table.format(
                    tmp_table=tmp_l2_pkgs, columns="(pkgname String)"
                )
            )
            if not self.sql_status:
                return

            _ = self.send_sql_request(
                (
                    self.sql.insert_into_tmp_table.format(tmp_table=tmp_l2_pkgs),
                    ((pkg,) for pkg in src_pkgs_by_level[2]),
                )
            )
            if not self.sql_status:
                return

            # filter level 2 packages by level 1 packages dependencies
            response = self.send_sql_request(
                (
                    self.sql.filter_l2_src_pkgs.format(
                        tmp_table1=tmp_l1_pkgs, tmp_table2=tmp_l2_pkgs
                    ),
                    {"branch": self.branch, "archs": tuple(self.arch)},
                )
            )
            if not self.sql_status:
                return

            # replace level 2 with filtered packages
            src_pkgs_by_level[2] = tuple(
                {
                    pkg
                    for pkg in [el[1] for el in response]  # type: ignore
                    if pkg in src_pkgs_by_level[2]
                }
            )

            # refill sorce packages temporary table
            _ = self.send_sql_request(
                self.sql.truncate_tmp_table.format(tmp_table=tmp_pkgs_list)
            )
            if not self.sql_status:
                return

            _ = self.send_sql_request(
                (
                    self.sql.insert_into_tmp_table.format(tmp_table=tmp_pkgs_list),
                    ((pkg,) for lvl in src_pkgs_by_level.values() for pkg in lvl),
                )
            )
            if not self.sql_status:
                return

        # get package acl
        response = self.send_sql_request(
            (
                self.sql.get_acl.format(tmp_table=tmp_pkgs_list),
                {"branch": self.branch},
            )
        )
        if not self.sql_status:
            return

        pkg_acl_dict = {}
        for pkg in response:  # type: ignore
            pkg_acl_dict[pkg[0]] = pkg[1][0]  # type: ignore

        # create temporary table for package dependencies
        tmp_table_pkg_dep = make_tmp_table_name("package_dependency")

        _ = self.send_sql_request(
            self.sql.create_tmp_table.format(
                tmp_table=tmp_table_pkg_dep, columns="(pkgname String, reqname String)"
            )
        )
        if not self.sql_status:
            return

        # get source dependencies
        if self.dptype in ("source", "both"):
            # populate the temporary table with package names and their source
            # dependencies
            _ = self.send_sql_request(
                (
                    self.sql.insert_src_deps.format(
                        tmp_deps=tmp_table_pkg_dep, tmp_table=tmp_pkgs_list
                    ),
                    {
                        "branch": self.branch,
                        "pkgs": list(input_pkgs),
                        "archs": tuple(self.arch),
                    },
                )
            )
            if not self.sql_status:
                return

        # get binary dependencies
        if self.dptype in ("binary", "both"):
            # populate the temporary table with package names and their binary
            # dependencies
            _ = self.send_sql_request(
                (
                    self.sql.insert_binary_deps.format(
                        tmp_table=tmp_pkgs_list, tmp_req=tmp_table_pkg_dep
                    ),
                    {
                        "branch": self.branch,
                        "archs": tuple(self.arch),
                        "pkgs": list(input_pkgs),
                    },
                )
            )
            if not self.sql_status:
                return

        # select all filtered package with dependencies
        response = self.send_sql_request(
            self.sql.get_all_filtred_pkgs_with_deps.format(tmp_table=tmp_table_pkg_dep)
        )
        if not self.sql_status:
            return

        pkgs_to_sort_dict = tuplelist_to_dict(response, 1)  # type: ignore

        if not pkgs_to_sort_dict:
            # nothing left after filtering
            self.status = True
            return

        if self.finitepkg:
            all_dependencies = []
            for pkg, deps in pkgs_to_sort_dict.items():
                for dep in deps:
                    if dep not in all_dependencies:
                        all_dependencies.append(dep)

            response = self.send_sql_request(
                (
                    self.sql.select_finite_pkgs.format(tmp_table=tmp_pkgs_list),
                    {"pkgs": tuple(all_dependencies)},
                )
            )
            if not self.sql_status:
                return

            filter_by_tops = join_tuples(response)  # type: ignore

        # check leaf, if true, get dependencies of leaf package
        if self.leaf:
            if self.leaf not in pkgs_to_sort_dict.keys():
                _ = self.store_error(
                    {
                        "message": f"Package {self.leaf} not in dependencies list for {self.packages}"
                    }
                )
                return

        pkg_ls_with_empty_reqs = []
        for pkg, reqs in pkgs_to_sort_dict.items():
            if not reqs:
                pkg_ls_with_empty_reqs.append(pkg)

        # sort list of dependencies by their dependencies
        sort = SortList(pkgs_to_sort_dict, self.packages)
        circle_deps, sorted_list = sort.sort_list()

        # create output dict with circle dependency
        result_dict = {}
        for name in sorted_list:
            result_dict[name] = []
            if name in circle_deps:
                result_dict[name] += list(circle_deps[name].keys())

        # if leaf, then select packages from the result list and their cyclic
        # dependencies on which the leaf package and create a dictionary
        if self.leaf:

            def recursive_search(pkgname, structure):
                for pkg in structure[pkgname]:
                    if pkg not in leaf_filter and pkg != pkgname:
                        leaf_filter.append(pkg)
                        recursive_search(pkg, structure)

            leaf_filter = []
            recursive_search(self.leaf, pkgs_to_sort_dict)

            if self.leaf not in leaf_filter:
                leaf_filter.append(self.leaf)

            # filter result dict by leaf packages
            result_dict = {
                key: value for (key, value) in result_dict.items() if key in leaf_filter
            }

        # list of result package names
        sorted_pkgs = tuple(result_dict.keys())

        # get output data for sorted package list
        # XXX: some source packages are filtered here if it has no binaries built from
        # it with specified archs due to using `INNER JOIN` in SQL request
        response = self.send_sql_request(
            self.sql.get_output_data.format(
                branch=self.branch,
                tmp_table=tmp_pkgs_list,
                tmp_table2=tmp_repo_state,
            )
        )
        if not self.sql_status:
            return

        # form list of packages with it information
        pkg_info_list = []
        for info in response:  # type: ignore
            for pkg, c_deps in result_dict.items():
                if info[0] == pkg:
                    # add empty list if not acl
                    if pkg not in pkg_acl_dict:
                        pkg_acl_dict[pkg] = []

                    pkg_info_list.append(
                        info  # type: ignore
                        + (c_deps,)
                        + (pkgs_to_sort_dict[pkg],)
                        + (pkg_acl_dict[pkg],)
                    )

        # filter result packages list by dependencies
        filter_pkgs = None
        if self.reqfilter or self.reqfiltersrc:
            if self.reqfilter:
                reqfilter_binpkgs = tuple(self.reqfilter)
            else:
                response = self.send_sql_request(
                    (
                        self.sql.req_filter_by_src,
                        {
                            "srcpkg": self.reqfiltersrc,
                            "branch": self.branch,
                            "archs": tuple(self.arch),
                        },
                    )
                )
                if not self.sql_status:
                    return

                reqfilter_binpkgs = join_tuples(response)  # type: ignore

            base_query = self.sql.req_filter_by_binary.format(
                pkg="{pkg}", tmp_table=tmp_pkgs_list
            )

            if len(reqfilter_binpkgs) == 1:
                base_query = base_query.format(pkg=reqfilter_binpkgs[0])
            else:
                last_query = None
                # TODO: rewrite that awful cyclic SQL build
                for pkg in reqfilter_binpkgs:
                    if not last_query:
                        last_query = base_query.format(pkg=pkg)

                    last_query = "{} AND pkg_name IN ({})" "".format(
                        last_query, base_query.format(pkg=pkg)
                    )

                base_query = last_query

            response = self.send_sql_request(
                (
                    self.sql.get_filter_pkgs.format(base_query=base_query),
                    {"branch": self.branch, "archs": tuple(self.arch)},
                )
            )
            if not self.sql_status:
                return

            filter_pkgs = join_tuples(response)  # type: ignore

        # sort pkg info list
        sorted_dict = {}
        for pkg in pkg_info_list:
            if (filter_pkgs and pkg[0] in filter_pkgs) or not filter_pkgs:
                sorted_dict[sorted_pkgs.index(pkg[0])] = pkg

        # add source package depth level
        result = []
        for el in dict(sorted(sorted_dict.items())).values():
            pkg_name = el[0]
            for k, v in src_pkgs_by_level.items():
                if pkg_name in v:
                    new_el = (*el, k)
                    break
            result.append(new_el)  # type: ignore

        if self.finitepkg:
            result = [pkg for pkg in result if pkg[0] in filter_by_tops]  # type: ignore
        # magic ends here
        PackageDependencies = namedtuple(
            "PackageDependencies",
            [
                "name",
                "version",
                "release",
                "epoch",
                "serial_",
                "sourcerpm",
                "branch",
                "archs",
                "buildtime",
                "cycle",
                "requires",
                "acl",
                "depth",
            ],
        )

        self.result = [PackageDependencies(*el)._asdict() for el in result]
        self.status = True


class PackageBuildDependency:
    """Retrieves packages dependent from given packages list."""

    def __init__(self, connection, **kwargs) -> None:
        self.conn = connection
        self.args = kwargs
        self.validation_results = None
        self.logger = get_logger(__name__)

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        self.validation_results = []

        if self.args["depth"] < 1 or self.args["depth"] > settings.DEPENDENCY_MAX_DEPTH:
            self.validation_results.append(
                f"dependency depth should be in range (1...{settings.DEPENDENCY_MAX_DEPTH})"
            )

        if None not in (self.args["filter_by_source"], self.args["filter_by_package"]):
            self.validation_results.append(
                "Parameters 'filter_by_src' and 'filter_by_package' can't be used together"
            )

        if self.validation_results != []:
            return False
        else:
            return True

    def get(self):
        # init BuildDependency class with args
        bd = BuildDependency(
            self.conn,
            self.args["packages"],
            self.args["branch"].lower(),
            self.args["archs"],
            self.args["leaf"],
            self.args["depth"],
            self.args["dptype"],
            self.args["filter_by_package"],
            self.args["filter_by_source"],
            self.args["finite_package"],
            self.args["oneandhalf"],
        )

        # build result
        if self.args["use_last_tasks"]:
            # get latest repo state including done tasks
            ls = LastRepoStateFromTask(self.conn, self.args["branch"])
            ls.build_repo_state()
            if not ls.status:
                return ls.error

            bd.build_dependencies(task_repo_hashes=ls.task_repo_pkgs)  # type: ignore
        else:
            bd.build_dependencies()

        # format result
        if bd.status:
            # result processing
            res = {
                "request_args": self.args,
                "length": len(bd.result),
                "dependencies": bd.result,
            }
            return res, 200
        else:
            return bd.error
