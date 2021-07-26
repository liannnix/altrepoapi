from collections import namedtuple

from api.base import APIWorker
from api.misc import lut
from database.packageset_sql import pkgsetsql


class PackagesetCompare(APIWorker):
    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = pkgsetsql
        super().__init__()

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        self.validation_results = []

        if self.args['pkgset1'] == '' or self.args['pkgset1'] not in lut.known_branches:
            self.validation_results.append(f"unknown package set name : {self.args['pkgset1']}")
            self.validation_results.append(f"allowed package set names are : {lut.known_branches}")

        if self.args['pkgset2'] == '' or self.args['pkgset2'] not in lut.known_branches:
            self.validation_results.append(f"unknown package set name : {self.args['pkgset2']}")
            self.validation_results.append(f"allowed package set names are : {lut.known_branches}")

        if self.validation_results != []:
            return False
        else:
            return True

    def get(self):
        self.pkgset1 = self.args['pkgset1']
        self.pkgset2 = self.args['pkgset2']


        self.conn.request_line = (
            self.sql.get_compare_info,
            {'pkgset1': self.pkgset1, 'pkgset2': self.pkgset2}
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
        
        Package = namedtuple('Package', ['name', 'version', 'release'])
        retval = []

        for el in response:
            retval.append(
                {
                    'pkgset1': self.pkgset1,
                    'pkgset2': self.pkgset2,
                    'package1': Package(*el[:3])._asdict(),
                    'package2': Package(*el[3:])._asdict()
                }
            )

        res = {
                'request_args' : self.args,
                'length': len(retval),
                'packages': retval
            }
        return res, 200
