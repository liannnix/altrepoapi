from collections import namedtuple

from settings import namespace as settings
from utils import get_logger, build_sql_error_response, logger_level as ll, tuplelist_to_dict

from api.misc import lut
from database.site_sql import sitesql

logger = get_logger(__name__)


class PackagesetPackages:
    DEBUG = settings.SQL_DEBUG

    def __init__(self, connection, **kwargs) -> None:
        self.conn = connection
        self.sql = sitesql
        self.args = kwargs
        self.validation_results = None

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
        self._log_error(severity)

    def _store_error(self, message, severity, http_code):
        self.error = message, http_code
        self._log_error(severity)

    def check_params(self):
        logger.debug(f"args : {self.args}")
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
            self._store_sql_error(response, ll.ERROR, 500)
            return self.error
        if not response:
            self._store_error(
                {"message": f"No data found in database for given parameters",
                "args": self.args},
                ll.INFO,
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


class PackagesetPackageHash:
    DEBUG = settings.SQL_DEBUG

    def __init__(self, connection, **kwargs) -> None:
        self.conn = connection
        self.sql = sitesql
        self.args = kwargs
        self.validation_results = None

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
        self._log_error(severity)

    def _store_error(self, message, severity, http_code):
        self.error = message, http_code
        self._log_error(severity)

    def check_params(self):
        logger.debug(f"args : {self.args}")
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
            self._store_sql_error(response, ll.ERROR, 500)
            return self.error
        if not response:
            self._store_error(
                {"message": f"Package '{self.name}' not found in package set '{self.branch}'",
                "args": self.args},
                ll.INFO,
                404
            )
            return self.error

        res = {
                'request_args' : self.args,
                'pkghash': str(response[0][0])
            }
        return res, 200


class PackagesetFindPackages:
    DEBUG = settings.SQL_DEBUG

    def __init__(self, connection, **kwargs) -> None:
        self.conn = connection
        self.sql = sitesql
        self.args = kwargs
        self.validation_results = None

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
        self._log_error(severity)

    def _store_error(self, message, severity, http_code):
        self.error = message, http_code
        self._log_error(severity)

    def check_params(self):
        logger.debug(f"args : {self.args}")
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
            if k.find(pkg_name) == -1:
                l_out.append(k)
            else:
                l_in.append(k)
        l_in.sort(key=lambda x: relevance_weight(x, pkg_name))
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
            self._store_sql_error(response, ll.ERROR, 500)
            return self.error
        if not response:
            self._store_error(
                {"message": f"Packages like '{self.name}' not found in database",
                "args": self.args},
                ll.INFO,
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


class AllPackagesets:
    DEBUG = settings.SQL_DEBUG

    def __init__(self, connection, **kwargs) -> None:
        self.conn = connection
        self.sql = sitesql
        self.args = kwargs
        self.validation_results = None

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
        self._log_error(severity)

    def _store_error(self, message, severity, http_code):
        self.error = message, http_code
        self._log_error(severity)

    def check_params(self):
        return True

    def get(self):
        self.conn.request_line = self.sql.get_all_pkgset_names
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, ll.ERROR, 500)
            return self.error
        if not response:
            self._store_error(
                {"message": f"No data not found in database",
                "args": self.args},
                ll.INFO,
                404
            )
            return self.error

        branches = response[0][0]
        res = [_ for _ in branches if _.startswith('s')]
        res += sorted([_ for _ in branches if _.startswith('p')], reverse=True)
        res += sorted([_ for _ in branches if _.startswith('c')], reverse=True)
        res += sorted([_ for _ in branches if _.startswith('t')], reverse=True)
        res += sorted([_ for _ in branches if _ not in res], reverse=True)

        res = {
                'length': len(res),
                'branches': res
            }
        return res, 200
