from collections import defaultdict, namedtuple

from utils import get_logger, tuplelist_to_dict, remove_duplicate

from api.base import APIWorker
from api.misc import lut
from database.package_sql import packagesql
from libs.conflict_filter import ConflictFilter
from libs.exceptions import SqlRequestError


class MisconflictPackages(APIWorker):
    def __init__(self, connection, packages, branch, archs, **kwargs) -> None:
        self.conn = connection
        self.args = kwargs
        self.sql = packagesql
        self.packages = packages
        self.branch = branch
        self.archs = archs
        self.result = {}
        super().__init__()

    def build_dependencies(self):
        # do all kind of black magic here
        self.packages = tuple(self.packages)
        if self.archs:
            if 'noarch' not in self.archs:
                self.archs.append('noarch')
        else:
            self.archs = lut.default_archs
        self.archs = tuple(self.archs)

        # get hash for package names
        self.conn.request_line = (self.sql.misconflict_get_hshs_by_pkgs, {
            'pkgs': self.packages, 'branch': self.branch, 'arch': self.archs
        })
        status, response = self.conn.send_request()
        if status is False:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return
        if not response:
            self._store_error(
                {"message": (
                    f"Packages {list(self.packages)} not in package set '{self.branch}'"
                    f" for archs {list(self.archs)}"
                )},
                self.ll.INFO, 404
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
                {"message": (
                    f"Packages ({set(self.packages) - input_pkgs_names}) not in"
                    f" package set '{self.branch}'"
                    f" for archs {list(self.archs)}"
                )},
                self.ll.INFO,
                404
            )
            return

        # get list of (input package | conflict package | conflict files)
        self.conn.request_line = (
            self.sql.misconflict_get_pkgs_with_conflict,
            {'hshs': input_pkg_hshs, 'branch': self.branch, 'arch': self.archs}
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
            [f_hashnames.add(_) for _ in el[2]]
        # 2. select real file names from DB
        self.conn.request_line = (
            self.sql.misconflict_get_fnames_by_fnhashs,
            {'hshs': tuple(f_hashnames)}
        )
        status, response = self.conn.send_request()
        if status is False:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.result
        if not response:
            self._store_error(
                {"message": f"Failed to get file names from database by hash"},
                self.ll.INFO,
                500
            )
            return

        f_hashnames = {}
        for r in response:
            f_hashnames[r[0]] = r[1]
        # 3. replase hashes by names in result
        new_hshs_files = []
        for el in hshs_files:
            new_hshs_files.append((
                *el[:2],
                [f_hashnames[_] for _ in el[2]],
                *el[3:]
            ))
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
                    'message': f"Error occured in ConflictFilter",
                    'error': e.dErrorArguments
                },
                self.ll.ERROR,
                500
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

        confl_pkgs = remove_duplicate(
            [pkg[1] for pkg in result_dict_cleanup.keys()]
        )

        # get main information of packages by package hashes
        self.conn.request_line = (
            self.sql.misconflict_get_meta_by_hshs,
            {'pkgs': tuple(confl_pkgs),'branch': self.branch, 'arch': self.archs}
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
                pkg = (pkg[0], pkg[1]) + \
                    name_info_dict[pkg[1]][:-1] + \
                    (list(intersect_pkg_archs),) + (files,)
                result_list_info.append(pkg)

        # magic ends here
        ConflictPackages = namedtuple('ConflictPackages', [
            'input_package', 'conflict_package', 'version', 'release',
            'epoch', 'archs', 'files_with_conflict'
        ])

        self.result = [ConflictPackages(*el)._asdict() for el in result_list_info]
        self.status = True


class PackageMisconflictPackages:
    def __init__(self, connection, **kwargs) -> None:
        self.conn = connection
        self.args = kwargs
        self.validation_results = None
        self.logger = get_logger(__name__)

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        self.validation_results = []
        if self.args['branch'] not in lut.known_branches:
            self.validation_results.append(f"unknown package set name : {self.args['branch']}")
            self.validation_results.append(f"allowed package set names are : {lut.known_branches}")

        if self.args['archs']:
            for arch in self.args['archs']:
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
        self.mp = MisconflictPackages(
            self.conn,
            self.args['packages'],
            self.args['branch'].lower(),
            self.args['archs']
        )
        
        # build result
        self.mp.build_dependencies()

        # format result
        if self.mp.status:
            # result processing
            res = {
                'request_args' : self.args,
                'length': len(self.mp.result),
                'conflicts': self.mp.result
            }
            return res, 200
        else:
            return self.mp.error
