from collections import namedtuple

from utils import tuplelist_to_dict, sort_branches, datetime_to_iso

from api.base import APIWorker
from api.misc import lut
from database.site_sql import sitesql


class PackagesetPackages(APIWorker):
    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sitesql
        super().__init__()

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        self.validation_results = []

        if self.args['branch'] == '' or self.args['branch'] not in lut.known_branches:
            self.validation_results.append(f"unknown package set name : {self.args['branch']}")
            self.validation_results.append(f"allowed package set names are : {lut.known_branches}")

        if self.args['package_type'] not in ('source', 'binary', 'all'):
            self.validation_results.append(
                f"package type should be one of 'source', 'binary' or 'all' not '{self.args['package_type']}'"
            )

        if self.args['group']:
            if self.args['group'] not in lut.pkg_groups:
                self.validation_results.append(f"unknown package category : {self.args['group']}")
                self.validation_results.append(f"allowed package categories : {lut.pkg_groups}")

        if self.args['buildtime'] and self.args['buildtime'] < 0:
            self.validation_results.append(f"package build time should be integer UNIX time representation")

        if self.validation_results != []:
            return False
        else:
            return True

    def get(self):
        self.pkg_type = self.args['package_type']
        self.branch = self.args['branch']
        self.group = self.args['group']
        self.buildtime = self.args['buildtime']

        if self.group is not None:
            self.group = f"AND pkg_group_ like '{self.group}%'"
        else:
            self.group = ''

        pkg_type_to_sql = {
            'source': (1,),
            'binary': (0,),
            'all': (1, 0)
        }
        sourcef = pkg_type_to_sql[self.pkg_type]

        self.conn.request_line = self.sql.get_repo_packages.format(
            buildtime=self.buildtime,
            branch=self.branch,
            group=self.group,
            src=sourcef
        )
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        if not response:
            self._store_error(
                {"message": f"No data found in database for given parameters",
                "args": self.args},
                self.ll.INFO,
                404
            )
            return self.error
        
        
        PkgMeta = namedtuple('PkgMeta', [
            'hash', 'name', 'version', 'release', 'buildtime', 'summary', 'maintainer',
            'category', 'changelog'
        ])

        retval = [PkgMeta(*el)._asdict() for el in response]

        res = {
                'request_args' : self.args,
                'length': len(retval),
                'packages': retval
            }
        return res, 200


class PackagesetPackageHash(APIWorker):
    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sitesql
        super().__init__()

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        self.validation_results = []

        if self.args['branch'] == '' or self.args['branch'] not in lut.known_branches:
            self.validation_results.append(f"unknown package set name : {self.args['branch']}")
            self.validation_results.append(f"allowed package set names are : {lut.known_branches}")

        if self.args['name'] == '':
            self.validation_results.append(
                f"package name should not be empty string"
            )

        if self.validation_results != []:
            return False
        else:
            return True

    def get(self):
        self.branch = self.args['branch']
        self.name = self.args['name']

        self.conn.request_line = self.sql.get_pkghash_by_name.format(
            branch=self.branch,
            name=self.name
        )
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        if not response:
            self._store_error(
                {"message": f"Package '{self.name}' not found in package set '{self.branch}'",
                "args": self.args},
                self.ll.INFO,
                404
            )
            return self.error

        res = {
                'request_args' : self.args,
                'pkghash': str(response[0][0]),
                'version': response[0][1],
                'release': response[0][2]
            }
        return res, 200


class PackagesetFindPackages(APIWorker):
    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sitesql
        super().__init__()

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        self.validation_results = []

        if self.args['branch'] is not None:
            if self.args['branch'] == '' or self.args['branch'] not in lut.known_branches:
                self.validation_results.append(f"unknown package set name : {self.args['branch']}")
                self.validation_results.append(f"allowed package set names are : {lut.known_branches}")

        if self.args['arch'] is not None:
            if self.args['arch'] not in lut.known_archs:
                self.validation_results.append(f"unknown package arch : {self.args['arch']}")
                self.validation_results.append(f"allowed archs are : {lut.known_archs}")

        if self.args['name'] is None or self.args['name'] == '':
            self.validation_results.append(
                f"package name should not be empty string"
            )
        elif len(self.args['name']) < 2:
            self.validation_results.append(
                f"package name should be 2 characters at least"
            )

        if self.validation_results != []:
            return False
        else:
            return True

    @staticmethod
    def _relevance_sort(pkgs_dict, pkg_name):
        """Dumb sorting for package names by relevance"""
        def relevance_weight(instr, substr):
            return (len(instr) + 100*instr.find(substr))
        l_in = []
        l_out = []
        for k in pkgs_dict.keys():
            if k.lower().find(pkg_name.lower()) == -1:
                l_out.append(k)
            else:
                l_in.append(k)
        l_in.sort(key=lambda x: relevance_weight(x.lower(), pkg_name.lower()))
        l_out.sort()
        return [(_, *pkgs_dict[_]) for _ in (l_in + l_out)]

    def get(self):
        self.name = self.args['name']
        self.arch = ''
        self.branch = ''
        if self.args['branch'] is not None:
            self.branch = f"AND pkgset_name = '{self.args['branch']}'"
        if self.args['arch'] is not None:
            self.arch = f"AND pkg_arch IN {(self.args['arch'],)}"
        else:
            self.arch = f"AND pkg_arch IN {(*lut.default_archs,)}"

        self.conn.request_line = self.sql.get_find_packages_by_name.format(
            branch=self.branch,
            name=self.name,
            arch=self.arch
        )
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        if not response:
            self._store_error(
                {"message": f"Packages like '{self.name}' not found in database",
                "args": self.args},
                self.ll.INFO,
                404
            )
            return self.error
        
        pkgs_sorted = self._relevance_sort(tuplelist_to_dict(response, 5), self.name)

        res = []
        PkgMeta = namedtuple('PkgMeta', ['branch', 'version', 'release', 'pkghash'])
        for pkg in pkgs_sorted:
            res.append({
                'name': pkg[0],
                'buildtime': pkg[2],
                'url': pkg[3],
                'summary': pkg[4],
                'category': pkg[5],
                'versions': [PkgMeta(*el)._asdict() for el in pkg[1]]
            })

        res = {
                'request_args' : self.args,
                'length': len(res),
                'packages': res
            }
        return res, 200


class AllPackagesets(APIWorker):
    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sitesql
        super().__init__()

    def get_pkgsets(self):
        self.conn.request_line = self.sql.get_all_pkgset_names
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        if not response:
            self._store_error(
                {"message": f"No data not found in database",
                "args": self.args},
                self.ll.INFO,
                404
            )
            return self.error

        pkg_branches = sort_branches(response[0][0])
        res = [{'branch': b, 'count': 0} for b in pkg_branches]

        res = {
                'length': len(res),
                'branches': res
            }
        return res, 200

    def get_with_pkgs_count(self):
        self.conn.request_line = self.sql.get_all_pkgset_names_with_pkg_count
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        if not response:
            self._store_error(
                {"message": f"No data not found in database",
                "args": self.args},
                self.ll.INFO,
                404
            )
            return self.error

        PkgCount = namedtuple('PkgCount', ['branch', 'count'])
        # sort package counts by branch
        pkg_branches = sort_branches([el[0] for el in response])
        pkg_counts = {el[0]: el[1] for el in response}
        res = [PkgCount(*(b, pkg_counts[b]))._asdict() for b in pkg_branches]

        res = {
                'length': len(res),
                'branches': res
            }
        return res, 200


class PkgsetCategoriesCount(APIWorker):
    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sitesql
        super().__init__()

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        self.validation_results = []

        if self.args['branch'] is not None:
            if self.args['branch'] == '' or self.args['branch'] not in lut.known_branches:
                self.validation_results.append(f"unknown package set name : {self.args['branch']}")
                self.validation_results.append(f"allowed package set names are : {lut.known_branches}")

        if self.args['package_type'] not in ('source', 'binary', 'all'):
            self.validation_results.append(
                f"package type should be one of 'source', 'binary' or 'all' not '{self.args['package_type']}'"
            )

        if self.validation_results != []:
            return False
        else:
            return True

    def get(self):
        self.branch = self.args['branch']
        self.pkg_type = self.args['package_type']

        pkg_type_to_sql = {
            'source': (1,),
            'binary': (0,),
            'all': (1, 0)
        }
        sourcef = pkg_type_to_sql[self.pkg_type]

        self.conn.request_line = self.sql.get_pkgset_groups_count.format(
            branch=self.branch,
            sourcef=sourcef
        )
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        if not response:
            self._store_error(
                {"message": f"No data not found in database",
                "args": self.args},
                self.ll.INFO,
                404
            )
            return self.error

        cat_raw = {el[0]: el[1] for el in response}
        res = []
        for cat in lut.pkg_groups:
            cnt = sum([v for k,v in cat_raw.items() if k.startswith(cat)])
            res.append({
                'category': cat,
                'count': cnt
            })

        res = {
                'request_args' : self.args,
                'length': len(res),
                'categories': res
            }
        return res, 200


class AllPackagesetArchs(APIWorker):
    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sitesql
        super().__init__()

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        self.validation_results = []

        if self.args['branch'] == '' or self.args['branch'] not in lut.known_branches:
            self.validation_results.append(f"unknown package set name : {self.args['branch']}")
            self.validation_results.append(f"allowed package set names are : {lut.known_branches}")

        if self.validation_results != []:
            return False
        else:
            return True

    def get_archs(self):
        self.branch = self.args['branch']
        self.conn.request_line = self.sql.get_all_bin_pkg_archs.format(branch=self.branch)
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        if not response:
            self._store_error(
                {"message": f"No data not found in database",
                "args": self.args},
                self.ll.INFO,
                404
            )
            return self.error

        archs = sorted([_ for _ in response[0][0] if _ not in ('x86_64-i586',)])
        res = [_ for _ in archs if _.startswith('x')]
        res += [_ for _ in archs if _.startswith('i')]
        res += [_ for _ in archs if _.startswith('n')]
        res += sorted([_ for _ in archs if _ not in res])

        res = [{'arch': _, 'count': 0} for _ in res]

        res = {
                'length': len(res),
                'archs': res
            }
        return res, 200

    def get_archs_with_src_count(self):
        self.branch = self.args['branch']
        self.conn.request_line = self.sql.get_all_src_cnt_by_bin_archs.format(branch=self.branch)
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        if not response:
            self._store_error(
                {"message": f"No data not found in database",
                "args": self.args},
                self.ll.INFO,
                404
            )
            return self.error

        archs = sorted([(*el,) for el in response], key=lambda val: val[1], reverse=True)
        res = [{'arch': _[0], 'count': _[1]} for _ in archs]

        res = {
                'length': len(res),
                'archs': res
            }
        return res, 200


class AllPackagesetsByHash(APIWorker):
    def __init__(self, connection, pkghash, **kwargs):
        self.pkghash = pkghash
        self.conn = connection
        self.args = kwargs
        self.sql = sitesql
        super().__init__()

    def get(self):
        self.conn.request_line = self.sql.get_all_pkgsets_by_hash.format(pkghash=self.pkghash)
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        if not response:
            self._store_error(
                {"message": f"No data not found in database",
                "args": self.args},
                self.ll.INFO,
                404
            )
            return self.error

        res = sort_branches([_[0] for _ in response])

        res = {
                'pkghash': str(self.pkghash),
                'length': len(res),
                'branches': res
            }
        return res, 200


class AllMaintainers(APIWorker):
    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sitesql
        super().__init__()

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        self.validation_results = []

        if self.args['branch'] == '' or self.args['branch'] not in lut.known_branches:
            self.validation_results.append(f"unknown package set name : {self.args['branch']}")
            self.validation_results.append(f"allowed package set names are : {lut.known_branches}")

        if self.validation_results != []:
            return False
        else:
            return True

    def get_maintainers(self):
        branch = self.args['branch']
        self.conn.request_line = self.sql.get_all_maintainers.format(branch=branch)
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        if not response:
            self._store_error(
                {"message": f"No data not found in database",
                 "args": self.args},
                self.ll.INFO,
                404
            )
            return self.error

        maintainers = sorted([(*el,) for el in response], key=lambda val: val[0])
        res = [{'pkg_packager': _[0], 'pkg_packager_email': _[1],'count_source_pkg': _[2]} for _ in maintainers]

        res = {
            'request_args': self.args,
            'length': len(res),
            'maintainers': res
        }

        return res, 200


class MaintainerInfo(APIWorker):
    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sitesql
        super().__init__()

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        self.validation_results = []

        if self.args['branch'] == '' or self.args['branch'] not in lut.known_branches:
            self.validation_results.append(f"unknown package set name : {self.args['branch']}")
            self.validation_results.append(f"allowed package set names are : {lut.known_branches}")

        if self.validation_results != []:
            return False
        else:
            return True

    def get_maintainer_info(self):
        maintainer_nickname = self.args['maintainer_nickname']
        branch = self.args['branch']
        self.conn.request_line = self.sql.get_maintainer_info.format(maintainer_nickname=maintainer_nickname, branch=branch)
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        if not response or response[0][0] == []:
            self._store_error(
                {"message": f"No data found in database for {maintainer_nickname} {branch}",
                 "args": self.args},
                self.ll.INFO,
                404
            )
            return self.error

        MaintainersInfo = namedtuple('MaintainersInfoModel', [
            'maintainer_name', 'maintainer_email', 'last_buildtime', 'count_source_pkg',
            'count_binary_pkg'
        ])
        res = MaintainersInfo(*response[0])._asdict()
        res['last_buildtime'] = datetime_to_iso(res['last_buildtime'])
        self.conn.request_line = self.sql.get_maintainer_branches.format(
            maintainer_nickname=maintainer_nickname
        )
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error

        MaintainerBranches = namedtuple('MaintainerBranches', ['branch', 'count'])
        branches = []
        for branch in sort_branches([el[0] for el in response]):
            for test in [MaintainerBranches(*b)._asdict() for b in response]:
                if test['branch'] == branch:
                    branches.append(test)
                    break
        res = {
            'request_args': self.args,
            'information': res,
            'branches': branches
        }

        return res, 200


class MaintainerPackages(APIWorker):
    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sitesql
        super().__init__()

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        self.validation_results = []

        if self.args['branch'] == '' or self.args['branch'] not in lut.known_branches:
            self.validation_results.append(f"unknown package set name : {self.args['branch']}")
            self.validation_results.append(f"allowed package set names are : {lut.known_branches}")

        if self.validation_results != []:
            return False
        else:
            return True

    def get_maintainer_packages(self):
        maintainer_nickname = self.args['maintainer_nickname']
        branch = self.args['branch']
        self.conn.request_line = self.sql.get_maintainer_pkg.format(maintainer_nickname=maintainer_nickname,
                                                                    branch=branch)
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        if not response:
            self._store_error(
                {"message": f"No data not found in database",
                 "args": self.args},
                self.ll.INFO,
                404
            )
            return self.error

        MaintainerPackages = namedtuple('MaintainerPackagesModel', [
            'name', 'buildtime', 'url', 'summary', 'version', 'release'
        ])
        res = [MaintainerPackages(*el)._asdict() for el in response]
        res = {
            'request_args': self.args,
            'length': len(res),
            'packages': res
        }

        return res, 200
