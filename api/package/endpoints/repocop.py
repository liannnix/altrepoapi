import datetime as dt
from collections import namedtuple

from utils import datetime_to_iso, tuplelist_to_dict, sort_branches

from api.base import APIWorker
from api.misc import lut
from database.package_sql import packagesql


class Repocop(APIWorker):
    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = packagesql
        super().__init__()

    def check_params_post(self):
        self.validation_results = []
        self.input_params = []
        self.known_param = ['pkg_name', 'pkg_version', 'pkg_release', 'pkg_arch', 'rc_srcpkg_name', 'rc_srcpkg_version',
                            'rc_srcpkg_release', 'rc_test_name', 'rc_test_status', 'rc_test_message', 'rc_test_date']
        for elem in self.args['json_data']['packages']:
            for key in elem.keys():
                self.input_params.append(key)
        if set(self.input_params) != set(self.known_param):
            self.validation_results.append(f'allowable values : {self.known_param}')
        if self.validation_results != []:
            return False
        else:
            return True

    def check_params_get(self):
        self.validation_results = []

        if self.args['srcpkg_version'] is not None and self.args['srcpkg_version'] == '':
            self.validation_results.append('srcpkg_version cannot be empty')
        if self.args['srcpkg_release'] is not None and self.args['srcpkg_release'] == '':
            self.validation_results.append('srcpkg_release cannot be empty')
        if self.validation_results != []:
            return False
        else:
            return True

    def post(self):
        json_ = self.args['json_data']['packages']
        for el in json_:
            el["rc_test_date"] = dt.datetime.fromisoformat(el["rc_test_date"])
        self.conn.request_line = (
            self.sql.insert_into_repocop,
            json_
        )
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        return "data loaded successfully", 201

    def get(self):
        self.source_pakage = self.args['srcpkg_name']
        if self.args['srcpkg_version'] is not None:
            version_cond = f"AND rc_srcpkg_version = '{self.args['srcpkg_version']}'"
        else:
            version_cond = ''
        if self.args['srcpkg_release'] is not None:
            release_cond = f"AND rc_srcpkg_release = '{self.args['srcpkg_release']}'"
        else:
            release_cond = ''
        self.conn.request_line = self.sql.get_out_repocop.format(
            pkgs=self.source_pakage,
            srcpkg_version=version_cond,
            srcpkg_release=release_cond
        )

        status, response = self.conn.send_request()
        if status is False:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error

        if not response:
            self._store_error(
                {"message": f"No results found in database for given parameters",
                 "args": self.args},
                self.ll.INFO,
                404
            )
            return self.error

        RepocopInfo = namedtuple('RepocopJsonModel', [
            'pkg_name', 'pkg_version', 'pkg_release', 'pkg_arch',
            'test_name', 'test_status', 'test_message', 'test_date'
        ])

        res = [RepocopInfo(*el)._asdict() for el in response]

        res = {
            'request_args': self.args,
            'length': len(res),
            'packages': res
        }

        return res, 200
