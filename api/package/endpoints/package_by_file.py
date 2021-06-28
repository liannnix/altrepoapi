from settings import namespace as settings
from utils import get_logger, build_sql_error_response, logger_level as ll
from utils import tuplelist_to_dict, convert_to_dict

from api.misc import lut
from database.package_sql import packagesql

logger = get_logger(__name__)


class PackageByFileName:
    DEBUG = settings.SQL_DEBUG

    def __init__(self, connection, **kwargs) -> None:
        self.conn = connection
        self.sql = packagesql
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

        if self.args['file'] == '':
            self.validation_results.append("file name not specified")

        if self.args['branch'] == '' or self.args['branch'] not in lut.known_branches:
            self.validation_results.append(f"unknown package set name : {self.args['branch']}")
            self.validation_results.append(f"allowed package set names are : {lut.known_branches}")

        if self.args['arch'] is not None:
            if self.args['arch'] not in lut.known_archs:
                self.validation_results.append(f"unknown package arch : {self.args['arch']}")
                self.validation_results.append(f"allowed archs are : {lut.known_archs}")

        if self.validation_results != []:
            return False
        else:
            return True

    def get(self):
        self.file = self.args['file']
        # replacae wildcards '*' with SQL-like '%'
        self.file = self.file.replace('*', '%')
        self.arch = self.args['arch']
        self.branch = self.args['branch']
        if self.arch:
            if 'noarch' not in self.arch:
                self.arch = (self.arch, 'noarch')
        else:
            self.arch = lut.known_archs
        self.arch = tuple(self.arch)
        
        file_names = {}
        # if file:
        self.conn.request_line = (
            self.sql.gen_table_fnhshs_by_file.format(tmp_table='TmpFileNames'),
            {'elem': self.file}
        )
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, ll.ERROR, 500)
            return self.error

        self.conn.request_line = self.sql.select_all_tmp_table.format(tmp_table='TmpFileNames')
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
        
        for f in response:
            file_names[f[0]] = f[1]

        self.conn.request_line = (
            self.sql.gen_table_hshs_by_file.format(
                tmp_table='TmpFiles',
                param=self.sql.gen_table_hshs_by_file_mod_hashname.format(tmp_table='TmpFileNames')
            ),
            {'branch': self.branch, 'arch': self.arch}
        )
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, ll.ERROR, 500)
            return self.error

        self.conn.request_line = self.sql.select_all_tmp_table.format(tmp_table='TmpFiles')
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

        ids_filename_dict = tuplelist_to_dict(response, 1)

        new_ids_filename_dict ={}

        for k, v in ids_filename_dict.items():
            new_ids_filename_dict[k] = [file_names[_] for _ in v]

        ids_filename_dict = new_ids_filename_dict

        self.conn.request_line = (
            self.sql.pkg_by_file_get_meta_by_hshs.format(tmp_table='TmpFiles'),
            {'branch': self.branch}
        )
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, ll.ERROR, 500)
            return self.error

        output_values = []
        for package in response:
            package += (ids_filename_dict[package[0]],)
            output_values.append(package[1:])

        output_params = ['pkgcs', 'name', 'sourcepackage', 'version', 'release',
                        'disttag', 'arch', 'branch', 'files']

        retval = convert_to_dict(output_params, tuple(output_values))

        res = {
                'request_args' : self.args,
                'length': len(retval),
                'packages': [_ for _ in retval.values()]
            }
        return res, 200


class PackageByFileMD5:
    DEBUG = settings.SQL_DEBUG

    def __init__(self, connection, **kwargs) -> None:
        self.conn = connection
        self.sql = packagesql
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

        if self.args['md5'] == '':
            self.validation_results.append("file MD5 checksum not specified")

        if self.args['branch'] == '' or self.args['branch'] not in lut.known_branches:
            self.validation_results.append(f"unknown package set name : {self.args['branch']}")
            self.validation_results.append(f"allowed package set names are : {lut.known_branches}")

        if self.args['arch'] is not None:
            if self.args['arch'] not in lut.known_archs:
                self.validation_results.append(f"unknown package arch : {self.args['arch']}")
                self.validation_results.append(f"allowed archs are : {lut.known_archs}")

        if self.validation_results != []:
            return False
        else:
            return True

    def get(self):
        self.md5 = self.args['md5']
        self.arch = self.args['arch']
        self.branch = self.args['branch']
        if self.arch:
            if 'noarch' not in self.arch:
                self.arch = (self.arch, 'noarch')
        else:
            self.arch = lut.known_archs
        self.arch = tuple(self.arch)
        
        self.conn.request_line = (
            self.sql.gen_table_hshs_by_file.format(
                tmp_table='TmpFiles',
                param=self.sql.gen_table_hshs_by_file_mod_md5
            ),
            {'branch': self.branch, 'arch': self.arch, 'elem': self.md5}
        )
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, ll.ERROR, 500)
            return self.error

        self.conn.request_line = self.sql.select_all_tmp_table.format(tmp_table='TmpFiles')
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

        ids_filename_dict = tuplelist_to_dict(response, 1)

        file_names = {}
        # 1. collect all files_hashname
        f_hashnames = set()
        for v in ids_filename_dict.values():
            [f_hashnames.add(_) for _ in v]
        # 2. select real file names from DB
        self.conn.request_line = self.sql.pkg_by_file_get_fnames_by_fnhashs.format(
            tmp_table='TmpFiles'
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

        for r in response:
            file_names[r[0]] = r[1]

        new_ids_filename_dict ={}

        for k, v in ids_filename_dict.items():
            new_ids_filename_dict[k] = [file_names[_] for _ in v]

        ids_filename_dict = new_ids_filename_dict

        self.conn.request_line = (
            self.sql.pkg_by_file_get_meta_by_hshs.format(tmp_table='TmpFiles'),
            {'branch': self.branch}
        )
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, ll.ERROR, 500)
            return self.error

        output_values = []
        for package in response:
            package += (ids_filename_dict[package[0]],)
            output_values.append(package[1:])

        output_params = ['pkgcs', 'name', 'sourcepackage', 'version', 'release',
                        'disttag', 'arch', 'branch', 'files']

        retval = convert_to_dict(output_params, tuple(output_values))

        res = {
                'request_args' : self.args,
                'length': len(retval),
                'packages': [_ for _ in retval.values()]
            }
        return res, 200
