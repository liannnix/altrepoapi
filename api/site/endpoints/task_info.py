from collections import namedtuple

from utils import datetime_to_iso

from api.base import APIWorker
from database.site_sql import sitesql


class TasksByPackage(APIWorker):
    def __init__(self, connection, **kwargs) -> None:
        super().__init__(connection, sitesql, **kwargs)

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
