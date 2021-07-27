from collections import namedtuple

from utils import datetime_to_iso

from api.base import APIWorker
from api.misc import lut
from database.site_sql import sitesql


class TasksByPackage(APIWorker):
    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sitesql
        super().__init__()

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        self.validation_results = []

        if self.args['name'] == '':
            self.validation_results.append(
                f"package name should not be empty string"
            )

        if self.validation_results != []:
            return False
        else:
            return True

    def get(self):
        self.name = self.args['name']

        self.conn.request_line = self.sql.get_tasks_by_pkg_name.format(
            name=self.name
        )
        
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error

        if not response:
            self._store_error(
                {"message": f"No data found in database for package '{self.name}'"},
                self.ll.INFO,
                404
            )
            return self.error
        
        TaskMeta = namedtuple('TaskMeta', ['id', 'state', 'changed', 'packages'])
        retval = [TaskMeta(*el)._asdict() for el in response]

        for task in retval:
            pkg_ls = []
            task['changed'] = datetime_to_iso(task['changed'])
            task['branch'] = task['packages'][0][1]
            task['owner'] = task['packages'][0][2]
            for pkg in task['packages']:
                subtask_type = pkg[3]
                if subtask_type == 'gear':
                    pkg_ls.append({'type': 'gear', 'name': pkg[4]})
                elif subtask_type in ('srpm', 'rebuild'):
                    pkg_ls.append({'type': 'package', 'name': pkg[5]})
                elif subtask_type == 'copy':
                    pkg_ls.append({'type': 'package', 'name': pkg[6]})
                else:
                    for el in pkg[4:]:
                        if el != "":
                            if el.endswith('.git'):
                                pkg_ls.append({'type': 'gear', 'name': el})
                            else:
                                pkg_ls.append({'type': 'package', 'name': el})
                            break
            task['packages'] = pkg_ls

        res = {
                'request_args' : self.args,
                'length': len(retval),
                'tasks': retval
            }
        return res, 200


class LastTaskPackages(APIWorker):
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

        if self.args['timedelta'] and self.args['timedelta'] < 0:
            self.validation_results.append(f"timedelta should be greater than 0")

        if self.validation_results != []:
            return False
        else:
            return True

    def get(self):
        self.branch = self.args['branch']
        self.timedelta = self.args['timedelta']

        self.conn.request_line = self.sql.get_last_pkgs_from_tasks.format(
            branch=self.branch,
            timedelta=self.timedelta
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
