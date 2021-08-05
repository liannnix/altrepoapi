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
        PkgMeta = namedtuple('PkgMeta', [
            'id', 'sub_id', 'repo', 'owner', 'type', 'dir', 'tag_id',
            'srpm_name', 'srpm_evr', 'package', 'pkg_from', 'changed'
        ])
        retval = [TaskMeta(*el)._asdict() for el in response]

        def build_gear_link(pkg):
            type_ = ''
            link_ = ''
            if pkg['type'] == 'copy':
                # 'copy' always has only 'subtask_package'
                type_ = 'search'
                link_ = pkg['package']
                if pkg['pkg_from'] != '':
                    link_ += f"&{pkg['pkg_from']}"
            elif pkg['type'] == 'delete' and pkg['srpm_name'] != '':
                # TODO: bug workaround for girar changes @ e74d8067009d
                type_ = 'srpm'
                link_ = '/'.join(
                    (lut.gitalt_base, 'srpms', pkg['srpm_name'][:1], (pkg['srpm_name'] + '.git'))
                )
                if pkg['srpm_evr'] != '':
                    link_ += f"?a=commit;hb={pkg['srpm_evr']}"
            elif pkg['type'] == 'delete':
                # 'delete' return only package name 
                type_ = 'delete'
                link_ = pkg['package']
            elif pkg['dir'] != '' or pkg['type'] == 'gear':
                # 'gear' and 'rebuild' + 'unknown' with gears
                type_ = 'gear'
                link_ = lut.gitalt_base + pkg['dir']
                if pkg['tag_id'] != '':
                    link_ += f"?a=commit;hb={pkg['tag_id']}"
            elif pkg['srpm_name'] != '' or pkg['type'] == 'srpm':
                # 'srpm' and 'rebuild' + 'unknown' with srpm
                type_ = 'srpm'
                link_ = '/'.join(
                    (lut.gitalt_base, 'srpms', pkg['srpm_name'][:1], (pkg['srpm_name'] + '.git'))
                )
                if pkg['srpm_evr'] != '':
                    link_ += f"?a=commit;hb={pkg['srpm_evr']}"

            return type_, link_

        tasks_for_pkg_names_search = []
        pkg_names = {}

        for task in retval:
            for p in task['packages']:
                if p[5] != '' and not p[5].startswith('/gears/'):
                    tasks_for_pkg_names_search.append((p[0], p[1]))

        if len(tasks_for_pkg_names_search) != 0:
            # create temporary table with task_id, subtask_id
            tmp_table = 'tmp_task_ids'
            self.conn.request_line = self.sql.create_tmp_table.format(
                tmp_table=tmp_table,
                columns='(task_id UInt32, subtask_id UInt32)'
            )
            status, response = self.conn.send_request()
            if not status:
                self._store_sql_error(response, self.ll.ERROR, 500)
                return self.error
            # insert task_id, subtask_id into temporary table
            self.conn.request_line = (
                self.sql.insert_into_tmp_table.format(tmp_table=tmp_table),
                ({'task_id': int(el[0]), 'subtask_id': int(el[1])} for el in tasks_for_pkg_names_search)
            )
            status, response = self.conn.send_request()
            if not status:
                self._store_sql_error(response, self.ll.ERROR, 500)
                return self.error
            # select package names by (task_id, subtask_id)
            self.conn.request_line = self.sql.get_pkg_names_by_task_ids.format(tmp_table=tmp_table)
            status, response = self.conn.send_request()
            if not status:
                self._store_sql_error(response, self.ll.ERROR, 500)
                return self.error
            if response:
                pkg_names = {(el[0], el[1]): el[2] for el in response if el[2] != ''}

        res = []

        for task in retval:
            pkg_ls = []
            pkg_type = ''
            pkg_link = ''
            for p in task['packages']:
                pkg = PkgMeta(*p)._asdict()
                if pkg['package'] != '':
                    pkg_name = pkg['package']
                elif pkg['srpm_name'] != '':
                    pkg_name = pkg['srpm_name']
                if pkg['dir'] != '' and not pkg['dir'].startswith('/gears/'):
                    try:
                        pkg_name = pkg_names[(int(pkg['id']), int(pkg['sub_id']))]
                        pkg['dir'] = f"/gears/{pkg_name[0]}/{pkg_name}.git"
                    except Exception as e:
                        pkg_name = pkg['dir'].split('/')[-1][:-4]
                pkg_type, pkg_link = build_gear_link(pkg)
                pkg_ls.append({
                    'type': pkg_type,
                    'link': pkg_link,
                    'name': pkg_name
                })

            res.append({
                'id': task['id'],
                'state': task['state'],
                'changed': datetime_to_iso(task['changed']),
                'branch': task['packages'][0][2],
                'owner': task['packages'][0][3],
                'packages': pkg_ls

            })
        
        res = {
                'request_args' : self.args,
                'length': len(res),
                'tasks': res
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
