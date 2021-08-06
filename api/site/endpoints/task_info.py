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

    @staticmethod
    def _build_gear_link(subtask, git_base_url):
        """Parse task gears

        Args:
            pkg (dict): subtask info with keys:
                ['type', 'dir', 'tag_id', 'srpm_name', 'srpm_evr', 'package', 'pkg_from']
            
            git_base_url (str): base git url for links ('http://git.altlinux.org')

        Returns:
            tuple: return package type [gear|srpm|copy|delete] and link (git)
        """
        type_ = ''
        link_ = ''
        if subtask['type'] == 'copy':
            # 'copy' always has only 'subtask_package'
            type_ = 'search'
            link_ = subtask['package']
            if subtask['pkg_from'] != '':
                link_ += f"&{subtask['pkg_from']}"
        elif subtask['type'] == 'delete' and subtask['srpm_name'] != '':
            # TODO: bug workaround for girar changes @ e74d8067009d
            type_ = 'srpm'
            link_ = f"{git_base_url}/srpms/{subtask['srpm_name'][0]}/{subtask['srpm_name']}.git"
            if subtask['srpm_evr'] != '':
                link_ += f"?a=commit;hb={subtask['srpm_evr']}"
        elif subtask['type'] == 'delete':
            # 'delete' return only package name 
            type_ = 'delete'
            link_ = subtask['package']
        elif subtask['dir'] != '' or subtask['type'] == 'gear':
            # 'gear' and 'rebuild' + 'unknown' with gears
            type_ = 'gear'
            link_ = git_base_url + subtask['dir']
            if subtask['tag_id'] != '':
                link_ += f"?a=commit;hb={subtask['tag_id']}"
        elif subtask['srpm_name'] != '' or subtask['type'] == 'srpm':
            # 'srpm' and 'rebuild' + 'unknown' with srpm
            type_ = 'srpm'
            link_ = f"{git_base_url}/srpms/{subtask['srpm_name'][0]}/{subtask['srpm_name']}.git"
            if subtask['srpm_evr'] != '':
                link_ += f"?a=commit;hb={subtask['srpm_evr']}"

        return type_, link_


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

        tasks_for_pkg_names_search = []
        pkg_names = {}

        for task in retval:
            for s in task['packages']:
                if s[5] != '' and not s[5].startswith('/gears/'):
                    tasks_for_pkg_names_search.append((s[0], s[1]))

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
        SubtaskMeta = namedtuple('SubtaskMeta', [
            'id', 'sub_id', 'repo', 'owner', 'type', 'dir', 'tag_id',
            'srpm_name', 'srpm_evr', 'package', 'pkg_from', 'changed'
        ])
        for task in retval:
            pkg_ls = []
            pkg_type = ''
            pkg_link = ''
            pkg_name = ''
            for s in task['packages']:
                subtask = SubtaskMeta(*s)._asdict()
                if subtask['package'] != '':
                    pkg_name = subtask['package']
                elif subtask['srpm_name'] != '':
                    pkg_name = subtask['srpm_name']
                if subtask['dir'] != '' and not subtask['dir'].startswith('/gears/'):
                    try:
                        pkg_name = pkg_names[(int(subtask['id']), int(subtask['sub_id']))]
                        subtask['dir'] = f"/gears/{pkg_name[0]}/{pkg_name}.git"
                    except Exception as e:
                        pkg_name = subtask['dir'].split('/')[-1][:-4]
                elif subtask['dir'].startswith('/gears/'):
                    pkg_name = subtask['dir'].split('/')[-1][:-4]
                pkg_type, pkg_link = self._build_gear_link(subtask, lut.gitalt_base)
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
