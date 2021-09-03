from collections import namedtuple

from settings import namespace as settings
from utils import get_logger, tuplelist_to_dict, join_tuples

from api.base import APIWorker
from api.misc import lut
from database.package_sql import packagesql
from libs.dependency_sorting import SortList


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
        self.sql = packagesql
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

    def build_dependencies(self):
        # do all kind of black magic here
        input_pkgs = self.packages
        depends_type_to_sql = {"source": (1,), "binary": (0,), "both": (1, 0)}
        sourcef = depends_type_to_sql[self.dptype]

        if self.arch:
            if "noarch" not in self.arch:
                self.arch.append("noarch")
        else:
            self.arch = ["x86_64", "noarch"]

        # store source packages by level
        # store source packages level 0
        src_pkgs_by_level = {0: tuple(input_pkgs)}

        def store_src_pkgs_levels(levels_dict: dict) -> bool:
            """Select and store packages from temporary table splitted by dependecy levels.

            Args:
                levels_dict (dict): packages dictionary (key: depth level (0..n), val: packages tuple)

            Returns:
                bool: False - if error ocured during SQL request
            """
            self.conn.request_line = self.sql.select_all_tmp_table.format(
                tmp_table="tmp_pkg_ls"
            )
            status, response = self.conn.send_request()
            if not status:
                return False
            pkgs = [el[0] for el in response]
            pkgs_prev_level = []
            for p in levels_dict.values():
                pkgs_prev_level += p
            levels_dict[max(levels_dict.keys()) + 1] = tuple(
                [pkg for pkg in pkgs if pkg not in pkgs_prev_level]
            )
            return True

        # create tmp table with list of packages
        tmp_table_name = "tmp_pkg_ls"
        self.conn.request_line = self.sql.create_tmp_table.format(
            tmp_table=tmp_table_name, columns="(pkgname String)"
        )
        status, response = self.conn.send_request()
        if status is False:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return

        # base query - first iteration, build requires depth 1
        self.conn.request_line = (
            self.sql.insert_build_req_deep_1.format(tmp_table=tmp_table_name),
            {
                "sfilter": sourcef,
                "pkgs": input_pkgs,
                "branch": self.branch,
                "union": list(input_pkgs),
            },
        )
        status, response = self.conn.send_request()
        if status is False:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return
        # store source packages level 1
        if not store_src_pkgs_levels(src_pkgs_by_level):
            self._store_sql_error(response, self.ll.ERROR, 500)
            return

        #  set depth to 2 if in 'oneandhalf' mode 
        if self.oneandhalf:
            self.depth = 2

        if self.depth > 1:
            # sql wrapper for increase depth
            deep_wrapper = self.sql.increase_depth_wrap.format(tmp_table=tmp_table_name)

            # process depth for every level and add results to pkg_ls
            for _ in range(self.depth - 1):
                self.conn.request_line = (
                    self.sql.insert_result_for_depth_level.format(
                        wrapper=deep_wrapper, tmp_table=tmp_table_name
                    ),
                    {"sfilter": sourcef, "branch": self.branch},
                )
                status, response = self.conn.send_request()
                if status is False:
                    self._store_sql_error(response, self.ll.ERROR, 500)
                    return
                # store source packages level 2..n
                if not store_src_pkgs_levels(src_pkgs_by_level):
                    self._store_sql_error(response, self.ll.ERROR, 500)
                    return

        # if 'oneandhalf' is set search dependencies of level 1 source packages from level 2 binary packages
        # filter level 2 packages from which level1 packages are depends
        if self.oneandhalf:
            # create and fill temporary tables for source packages filtering
            # level 1 packages
            self.conn.request_line = self.sql.create_tmp_table.format(
                tmp_table="l1_pkgs", columns="(pkgname String)"
            )
            status, response = self.conn.send_request()
            if status is False:
                self._store_sql_error(response, self.ll.ERROR, 500)
                return

            self.conn.request_line = (
                self.sql.insert_into_tmp_table.format(tmp_table="l1_pkgs"),
                ((pkg,) for pkg in src_pkgs_by_level[1]),
            )
            status, response = self.conn.send_request()
            if status is False:
                self._store_sql_error(response, self.ll.ERROR, 500)
                return

            # level 1 packages
            self.conn.request_line = self.sql.create_tmp_table.format(
                tmp_table="l2_pkgs", columns="(pkgname String)"
            )
            status, response = self.conn.send_request()
            if status is False:
                self._store_sql_error(response, self.ll.ERROR, 500)
                return

            self.conn.request_line = (
                self.sql.insert_into_tmp_table.format(tmp_table="l2_pkgs"),
                ((pkg,) for pkg in src_pkgs_by_level[2]),
            )
            status, response = self.conn.send_request()
            if status is False:
                self._store_sql_error(response, self.ll.ERROR, 500)
                return

            # filter level 2 packages by level 1 packages dependencies
            self.conn.request_line = (
                self.sql.filter_l2_src_pkgs.format(tmp_table1="l1_pkgs", tmp_table2="l2_pkgs"),
                {"branch": self.branch},
            )
            status, response = self.conn.send_request()
            if status is False:
                self._store_sql_error(response, self.ll.ERROR, 500)
                return
            # replace level 2 with filtered packages
            src_pkgs_by_level[2] = tuple(
                {
                    pkg
                    for pkg in [el[1] for el in response]
                    if pkg in src_pkgs_by_level[2]
                }
            )
            # refill sorce packages temporary table
            self.conn.request_line = self.sql.truncate_tmp_table.format(
                tmp_table=tmp_table_name
            )
            status, response = self.conn.send_request()
            if status is False:
                self._store_sql_error(response, self.ll.ERROR, 500)
                return

            self.conn.request_line = (
                self.sql.insert_into_tmp_table.format(tmp_table=tmp_table_name),
                ((pkg,) for lvl in src_pkgs_by_level.values() for pkg in lvl),
            )
            status, response = self.conn.send_request()
            if status is False:
                self._store_sql_error(response, self.ll.ERROR, 500)
                return

        # get package acl
        self.conn.request_line = (
            self.sql.get_acl.format(tmp_table=tmp_table_name),
            {"branch": self.branch},
        )
        status, response = self.conn.send_request()
        if status is False:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return

        pkg_acl_dict = {}
        for pkg in response:
            pkg_acl_dict[pkg[0]] = pkg[1][0]

        # create temporary table for package dependencies
        tmp_table_pkg_dep = "package_dependency"
        self.conn.request_line = self.sql.create_tmp_table.format(
            tmp_table=tmp_table_pkg_dep, columns="(pkgname String, reqname String)"
        )
        status, response = self.conn.send_request()
        if status is False:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return

        # get source dependencies
        if self.dptype in ("source", "both"):
            # populate the temporary table with package names and their source
            # dependencies
            self.conn.request_line = (
                self.sql.insert_src_deps.format(
                    tmp_deps=tmp_table_pkg_dep, tmp_table=tmp_table_name
                ),
                {"branch": self.branch, "pkgs": list(input_pkgs)},
            )
            status, response = self.conn.send_request()
            if status is False:
                self._store_sql_error(response, self.ll.ERROR, 500)
                return

        # get binary dependencies
        if self.dptype in ("binary", "both"):
            # populate the temporary table with package names and their binary
            # dependencies
            self.conn.request_line = (
                self.sql.insert_binary_deps.format(
                    tmp_table=tmp_table_name, tmp_req=tmp_table_pkg_dep
                ),
                {"branch": self.branch, "archs": tuple(self.arch)},
            )
            status, response = self.conn.send_request()
            if status is False:
                self._store_sql_error(response, self.ll.ERROR, 500)
                return

        # select all filtered package with dependencies
        self.conn.request_line = self.sql.get_all_filtred_pkgs_with_deps.format(
            tmp_table=tmp_table_pkg_dep
        )
        status, response = self.conn.send_request()
        if status is False:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return

        pkgs_to_sort_dict = tuplelist_to_dict(response, 1)

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

            self.conn.request_line = (
                self.sql.select_finite_pkgs.format(tmp_table=tmp_table_name),
                {"pkgs": tuple(all_dependencies)},
            )
            status, response = self.conn.send_request()
            if status is False:
                self._store_sql_error(response, self.ll.ERROR, 500)
                return

            filter_by_tops = join_tuples(response)

        # check leaf, if true, get dependencies of leaf package
        if self.leaf:
            if self.leaf not in pkgs_to_sort_dict.keys():
                self._store_error(
                    {
                        "message": f"Package {self.leaf} not in dependencies list for {self.packages}"
                    },
                    self.ll.INFO,
                    404,
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
        self.conn.request_line = (
            self.sql.get_output_data.format(tmp_table=tmp_table_name),
            {"branch": self.branch},
        )
        status, response = self.conn.send_request()
        if status is False:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return

        # form list of packages with it information
        pkg_info_list = []
        for info in response:
            for pkg, c_deps in result_dict.items():
                if info[0] == pkg:
                    # add empty list if not acl
                    if pkg not in pkg_acl_dict:
                        pkg_acl_dict[pkg] = []

                    pkg_info_list.append(
                        info
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
                self.conn.request_line = (
                    self.sql.req_filter_by_src,
                    {"srcpkg": self.reqfiltersrc, "branch": self.branch},
                )
                status, response = self.conn.send_request()
                if status is False:
                    self._store_sql_error(response, self.ll.ERROR, 500)
                    return

                reqfilter_binpkgs = join_tuples(response)

            base_query = self.sql.req_filter_by_binary.format(
                pkg="{pkg}", tmp_table=tmp_table_name
            )

            if len(reqfilter_binpkgs) == 1:
                base_query = base_query.format(pkg=reqfilter_binpkgs[0])
            else:
                last_query = None
                # FIXME: rewrite that awful cyclic SQL build!!!
                for pkg in reqfilter_binpkgs:
                    if not last_query:
                        last_query = base_query.format(pkg=pkg)

                    last_query = "{} AND pkg_name IN ({})" "".format(
                        last_query, base_query.format(pkg=pkg)
                    )

                base_query = last_query

            self.conn.request_line = (
                self.sql.get_filter_pkgs.format(base_query=base_query),
                {"branch": self.branch, "archs": tuple(self.arch)},
            )
            status, response = self.conn.send_request()
            if status is False:
                self._store_sql_error(response, self.ll.ERROR, 500)
                return

            filter_pkgs = join_tuples(response)

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
            result.append(new_el)

        if self.finitepkg:
            result = [pkg for pkg in result if pkg[0] in filter_by_tops]
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
        if self.args["branch"] not in lut.known_branches:
            self.validation_results.append(
                f"unknown package set name : {self.args['branch']}"
            )
            self.validation_results.append(
                f"allowed package set names are : {lut.known_branches}"
            )

        if self.args["arch"]:
            for arch in self.args["arch"]:
                if arch not in lut.known_archs:
                    self.validation_results.append(f"unknown package arch : {arch}")

        if self.args["depth"] < 1 or self.args["depth"] > settings.DEPENDENCY_MAX_DEPTH:
            self.validation_results.append(
                f"dependency depth should be in range (1...{settings.DEPENDENCY_MAX_DEPTH})"
            )

        if self.args["dptype"] not in ("source", "binary", "both"):
            self.validation_results.append(
                f"dependency type should be one of 'source', 'binary' or 'both' not '{self.args['dptype']}'"
            )

        if None not in (self.args["filter_by_source"], self.args["filter_by_package"]):
            self.validation_results.append(
                f"Parameters 'filter_by_src' and 'filter_by_package' can't be used together"
            )

        if self.validation_results != []:
            return False
        else:
            return True

    def get(self):
        # arguments processing
        pass
        # init BuildDependency class with args
        self.bd = BuildDependency(
            self.conn,
            self.args["packages"],
            self.args["branch"].lower(),
            self.args["arch"],
            self.args["leaf"],
            self.args["depth"],
            self.args["dptype"],
            self.args["filter_by_package"],
            self.args["filter_by_source"],
            self.args["finite_package"],
            self.args["oneandhalf"],
        )

        # build result
        self.bd.build_dependencies()

        # format result
        if self.bd.status:
            # result processing
            res = {
                "request_args": self.args,
                "length": len(self.bd.result),
                "dependencies": self.bd.result,
            }
            return res, 200
        else:
            return self.bd.error
