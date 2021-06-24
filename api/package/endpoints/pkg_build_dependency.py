from utils import get_logger, build_sql_error_response
from utils import tuplelist_to_dict, join_tuples, logger_level as ll, convert_to_dict
from database.package_sql import packagesql
from settings import namespace as settings
from api.misc import lut
from libs.dependency_sorting import SortList

logger = get_logger(__name__)


class BuildDependency:
    def __init__(
        self, connection, packages, branch, archs, leaf, depth,
        dptype, filterbybin, filterbysrc, finitepkg, debug_
    ):
        self.conn = connection
        self.sql = packagesql
        self.DEBUG = debug_
        self.status = False
        self.packages = packages
        self.branch = branch
        self.arch = archs
        self.leaf = leaf
        self.depth = depth
        self.dptype = dptype
        self.reqfilter = filterbybin
        self.reqfiltersrc = filterbysrc
        self.finitepkg = finitepkg
        self.result = None

    def _log_error(self, severity):
        if severity == ll.CRITICAL:
            logger.critical(self.error)
        elif severity == ll.ERROR:
            logger.error(self.error)
        elif severity == ll.WARNING:
            logger.warning(self.error)
        elif severity == ll.INFO:
            logger.info(self.error)
        else:
            logger.debug(self.error)

    def _store_sql_error(self, message, severity, http_code):
        self.error = build_sql_error_response(message, self, http_code, self.DEBUG)
        self.status = False
        self._log_error(severity)

    def _store_error(self, message, severity, http_code):
        self.error = message, http_code
        self.status = False
        self._log_error(severity)

    def build_dependencies(self):
        # do all kind of black magic here
        input_pkgs = self.packages
        depends_type_to_sql = {
            'source': (1,),
            'binary': (0,),
            'both': (1, 0)
        }
        sourcef = depends_type_to_sql[self.dptype]

        if self.arch:
            if 'noarch' not in self.arch:
                self.arch.append('noarch')
        else:
            self.arch = ['x86_64', 'noarch']

        # create tmp table with list of packages
        tmp_table_name = 'tmp_pkg_ls'
        self.conn.request_line = self.sql.create_tmp_table.format(
            tmp_table=tmp_table_name, columns='(pkgname String)'
        )
        status, response = self.conn.send_request()
        if status is False:
            self._store_sql_error(response, ll.ERROR, 500)
            return self.result

        # base query - first iteration, build requires depth 1
        self.conn.request_line = (
            self.sql.insert_build_req_deep_1.format(tmp_table=tmp_table_name), {
                'sfilter': sourcef,
                'pkgs': input_pkgs,
                'branch': self.branch,
                'union': list(input_pkgs)
            }
        )
        status, response = self.conn.send_request()
        if status is False:
            self._store_sql_error(response, ll.ERROR, 500)
            return self.result

        if self.depth > 1:
            # sql wrapper for increase depth
            deep_wrapper = self.sql.increase_depth_wrap.format(
                tmp_table=tmp_table_name
            )

            # process depth for every level and add results to pkg_ls
            for _ in range(self.depth - 1):
                self.conn.request_line = (self.sql.insert_result_for_depth_level.format(
                    wrapper=deep_wrapper, tmp_table=tmp_table_name
                ), {'sfilter': sourcef, 'branch': self.branch})
            status, response = self.conn.send_request()
            if status is False:
                self._store_sql_error(response, ll.ERROR, 500)
                return self.result

        self.conn.request_line = (
            self.sql.get_acl.format(tmp_table=tmp_table_name),
            {'branch': self.branch}
        )
        status, response = self.conn.send_request()
        if status is False:
            self._store_sql_error(response, ll.ERROR, 500)
            return self.result

        # get package acl
        pkg_acl_dict = {}
        for pkg in response:
            pkg_acl_dict[pkg[0]] = pkg[1][0]

        tmp_table_pkg_dep = 'package_dependency'
        self.conn.request_line = self.sql.create_tmp_table.format(
            tmp_table=tmp_table_pkg_dep,
            columns='(pkgname String, reqname String)'
        )
        status, response = self.conn.send_request()
        if status is False:
            self._store_sql_error(response, ll.ERROR, 500)
            return self.result

        # get source dependencies
        if self.dptype in ('source', 'both'):
            # populate the temporary table with package names and their source
            # dependencies
            self.conn.request_line = (
                self.sql.insert_src_deps.format(
                    tmp_deps=tmp_table_pkg_dep, tmp_table=tmp_table_name), {
                    'branch': self.branch, 'pkgs': list(input_pkgs)
                }
            )
            status, response = self.conn.send_request()
            if status is False:
                self._store_sql_error(response, ll.ERROR, 500)
                return self.result

        # get binary dependencies
        if self.dptype in ('binary', 'both'):
            # populate the temporary table with package names and their binary
            # dependencies
            self.conn.request_line = (
                self.sql.insert_binary_deps.format(
                    tmp_table=tmp_table_name, tmp_req=tmp_table_pkg_dep
                ),
                {'branch': self.branch, 'archs': tuple(self.arch)}
            )
            status, response = self.conn.send_request()
            if status is False:
                self._store_sql_error(response, ll.ERROR, 500)
                return self.result

        # select all filtered package with dependencies
        self.conn.request_line = self.sql.get_all_filtred_pkgs_with_deps
        status, response = self.conn.send_request()
        if status is False:
            self._store_sql_error(response, ll.ERROR, 500)
            return self.result

        pkgs_to_sort_dict = tuplelist_to_dict(response, 1)

        if not pkgs_to_sort_dict:
            self.status = True
            return self.result

        if self.finitepkg:
            all_dependencies = []
            for pkg, deps in pkgs_to_sort_dict.items():
                for dep in deps:
                    if dep not in all_dependencies:
                        all_dependencies.append(dep)

            self.conn.request_line = (
                self.sql.select_finite_pkgs.format(tmp_table=tmp_table_name),
                {'pkgs': tuple(all_dependencies)}
            )
            status, response = self.conn.send_request()
            if status is False:
                self._store_sql_error(response, ll.ERROR, 500)
                return self.result

            filter_by_tops = join_tuples(response)

        # check leaf, if true, get dependencies of leaf package
        if self.leaf:
            if self.leaf not in pkgs_to_sort_dict.keys():
                self._store_error(
                    {"message": f"Package {self.leaf} not in dependencies list for {self.packages}"},
                    ll.INFO,
                    404
                )
                return self.result

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
                key: value for (key, value) in result_dict.items()
                if key in leaf_filter
            }

        # list of result package names
        sorted_pkgs = tuple(result_dict.keys())

        # get output data for sorted package list
        self.conn.request_line = (
            self.sql.get_output_data.format(tmp_table=tmp_table_name),
            {'branch': self.branch}
        )
        status, response = self.conn.send_request()
        if status is False:
            self._store_sql_error(response, ll.ERROR, 500)
            return self.result

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
                self.conn.request_line = (self.sql.req_filter_by_src, {
                    'srcpkg': self.reqfiltersrc,
                    'branch': self.branch
                })
                status, response = self.conn.send_request()
                if status is False:
                    self._store_sql_error(response, ll.ERROR, 500)
                    return self.result

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

                    last_query = "{} AND pkg_name IN ({})" \
                                "".format(last_query, base_query.format(pkg=pkg))

                base_query = last_query

            self.conn.request_line = (
                self.sql.get_filter_pkgs.format(base_query=base_query),
                {'branch': self.branch, 'archs': tuple(self.arch)}
            )
            status, response = self.conn.send_request()
            if status is False:
                self._store_sql_error(response, ll.ERROR, 500)
                return self.result

            filter_pkgs = join_tuples(response)

        # sort pkg info list
        sorted_dict = {}
        for pkg in pkg_info_list:
            if (filter_pkgs and pkg[0] in filter_pkgs) or not filter_pkgs:
                # FIXME: find out what below 'if' is for? doesn't make sense at a glance
                # if task_id:
                #     if pkg[0] not in input_pkgs:
                #         sorted_dict[sorted_pkgs.index(pkg[0])] = pkg
                # else:
                sorted_dict[sorted_pkgs.index(pkg[0])] = pkg

        sorted_dict = list(dict(sorted(sorted_dict.items())).values())

        if self.finitepkg:
            sorted_dict = [pkg for pkg in sorted_dict if pkg[0] in filter_by_tops]
        # magic ends here
        keys = ['name', 'version', 'release', 'epoch', 'serial_', 'sourcerpm',
                'branch', 'archs', 'buildtime', 'cycle', 'requires', 'acl']
        self.result = convert_to_dict(keys, sorted_dict)        
        self.status = True


class PackageBuildDependency:
    DEBUG = settings.SQL_DEBUG

    def __init__(self, connection, **kwargs) -> None:
        self.conn = connection
        self.sql = packagesql
        self.args = kwargs
        self.validation_results = None

    def check_params(self):
        logger.debug(f"args : {self.args}")
        self.validation_results = []
        if self.args['branch'] not in lut.known_branches:
            self.validation_results.append(f"unknown package set name : {self.args['branch']}")
            self.validation_results.append(f"allowed package set names are : {lut.known_branches}")

        if self.args['arch']:
            for arch in self.args['arch']:
                if arch not in lut.known_archs:
                    self.validation_results.append(f"unknown package arch : {arch}")

        if self.args['depth'] < 1 or self.args['depth'] > settings.DEPENDENCY_MAX_DEPTH:
            self.validation_results.append(
                f"dependency depth should be in range (1...{settings.DEPENDENCY_MAX_DEPTH})"
            )

        if self.args['dptype'] not in ('source', 'binary', 'both'):
            self.validation_results.append(
                f"dependency type should be one of 'source', 'binary' or 'both' not '{self.args['dptype']}'"
            )

        if None not in (self.args['filter_by_source'], self.args['filter_by_package']):
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
            self.args['package'],
            self.args['branch'].lower(),
            self.args['arch'],
            self.args['leaf'],
            self.args['depth'],
            self.args['dptype'],
            self.args['filter_by_package'],
            self.args['filter_by_source'],
            self.args['finite_package'],
            self.DEBUG)
        
        # build result
        self.bd.build_dependencies()

        # format result
        if self.bd.status:
            # result processing
            res = {
                'request_args' : self.args,
                'dependencies': [_ for _ in self.bd.result.values()]
            }
            res['length'] = len(res['dependencies'])
            return res, 200
        else:
            return self.bd.error
