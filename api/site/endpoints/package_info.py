from collections import namedtuple

from settings import namespace as settings
from utils import get_logger, build_sql_error_response, logger_level as ll
from utils import datetime_to_iso

from api.misc import lut
from database.site_sql import sitesql

logger = get_logger(__name__)


class PackageChangelog:
    DEBUG = settings.SQL_DEBUG

    def __init__(self, connection, pkghash, **kwargs) -> None:
        self.conn = connection
        self.sql = sitesql
        self.args = kwargs
        self.pkghash = pkghash
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

        if self.args['changelog_last'] < 1:
            self.validation_results.append(f"changelog history length should be not less than 1")

        if self.validation_results != []:
            return False
        else:
            return True

    def get(self):
        self.chlog_length = self.args['changelog_last']
        self.conn.request_line = self.sql.get_pkg_changelog.format(pkghash=self.pkghash)
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, ll.ERROR, 500)
            return self.error
        if not response:
            self._store_error(
                {"message": f"No packages found in last packages with hash {self.pkghash}",
                "args": self.args},
                ll.INFO,
                404
            )
            return self.error

        changelog_list = []
        for changelog in response[0]:
            i = 0
            for v in changelog:
                changelog_dict = {}
                changelog_dict['date']    = datetime_to_iso(v[0])
                changelog_dict['name']    = v[1]
                changelog_dict['evr']     = v[2]
                changelog_dict['message'] = v[3]
                changelog_list.append(changelog_dict)
                i += 1
                if i >= self.chlog_length:
                    break

        res = {
                'pkghash': str(self.pkghash),
                'request_args' : self.args,
                'length': len(changelog_list),
                'changelog': changelog_list
            }

        return res, 200


class PackageInfo:
    DEBUG = settings.SQL_DEBUG

    def __init__(self, connection, pkghash, **kwargs) -> None:
        self.conn = connection
        self.sql = sitesql
        self.args = kwargs
        self.pkghash = pkghash
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

        if self.args['changelog_last'] < 1:
            self.validation_results.append(f"changelog history length should be not less than 1")

        if self.validation_results != []:
            return False
        else:
            return True

    def get(self):
        self.branch = self.args['branch']
        self.chlog_length = self.args['changelog_last']
        PkgMeta = namedtuple('PkgMeta', [
            'name', 'version', 'release', 'buildtime', 'url', 'license', 
            'summary', 'description', 'packager', 'packager_email', 'category'
        ])
        # get package info
        self.conn.request_line = self.sql.get_pkg_info.format(pkghash=self.pkghash)
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, ll.ERROR, 500)
            return self.error
        if not response:
            self._store_error(
                {"message": f"No packages found in last packages with hash {self.pkghash}",
                "args": self.args},
                ll.INFO,
                404
            )
            return self.error
        pkg_info = PkgMeta(*response[0])._asdict()
        # get package task
        pkg_task = 0
        self.conn.request_line = self.sql.get_pkg_task_by_hash.format(pkghash=self.pkghash)
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, ll.ERROR, 500)
            return self.error
        if response:
            pkg_task = response[0][0]
        # get package maintaners
        pkg_maintainers = []
        self.conn.request_line = self.sql.get_pkg_maintaners.format(
            name=pkg_info['name']
        )
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, ll.ERROR, 500)
            return self.error
        pkg_maintainers = [{'name': _[0], 'email': _[1]} for _ in response]
        # get package ACLs
        pkg_acl = []
        self.conn.request_line = self.sql.get_pkg_acl.format(
            name=pkg_info['name'],
            branch=self.branch
        )
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, ll.ERROR, 500)
            return self.error
        if response:
            pkg_acl = response[0][0]
        # get package versions
        # FIXME: slow request :(
        pkg_versions = []
        self.conn.request_line = self.sql.get_pkg_versions.format(
            name=pkg_info['name']
        )
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, ll.ERROR, 500)
            return self.error
        PkgVersions = namedtuple('PkgVersions', ['branch', 'version', 'release', 'pkghash'])
        pkg_versions = [PkgVersions(*el)._asdict() for el in response]
        # get provided binary packages
        bin_packages_list = []
        self.conn.request_line = self.sql.get_binary_pkgs.format(pkghash=self.pkghash)
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, ll.ERROR, 500)
            return self.error
        bin_packages_list = [_[0] for _ in response]
        # get package changelog
        self.conn.request_line = self.sql.get_pkg_changelog.format(pkghash=self.pkghash)
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, ll.ERROR, 500)
            return self.error
        if not response:
            self._store_error(
                {"message": f"No packages found in last packages with hash {self.pkghash}",
                "args": self.args},
                ll.INFO,
                404
            )
            return self.error

        changelog_list = []
        for changelog in response[0]:
            i = 0
            for v in changelog:
                changelog_dict = {}
                changelog_dict['date']    = datetime_to_iso(v[0])
                changelog_dict['name']    = v[1]
                changelog_dict['evr']     = v[2]
                changelog_dict['message'] = v[3]
                changelog_list.append(changelog_dict)
                i += 1
                if i >= self.chlog_length:
                    break

        res = {
                'pkghash': str(self.pkghash),
                'request_args' : self.args,
                **pkg_info,
                'task': pkg_task,
                'packages': bin_packages_list,
                'changelog': changelog_list,
                'maintainers': pkg_maintainers,
                'acl': pkg_acl,
                'versions': pkg_versions
            }

        return res, 200


class AllPackageArchs:
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
        self.conn.request_line = self.sql.get_all_bin_pkg_archs
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

        archs = sorted([_ for _ in response[0][0] if _ not in ('x86_64-i586',)])
        res = [_ for _ in archs if _.startswith('x')]
        res += [_ for _ in archs if _.startswith('i')]
        res += [_ for _ in archs if _.startswith('n')]
        res += sorted([_ for _ in archs if _ not in res])

        res = {
                'length': len(res),
                'archs': res
            }
        return res, 200
