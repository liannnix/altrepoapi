from copy import deepcopy
from collections import defaultdict
from utils import get_logger, build_sql_error_response
from utils import join_tuples, remove_duplicate, logger_level as ll
from database.task_sql import tasksql
from api.task.endpoints.task_repo import TaskRepo
from api.misc import lut
from settings import namespace as settings

logger = get_logger(__name__)

class TaskDiff:
    DEBUG = settings.SQL_DEBUG

    def __init__(self, connection, id):
        self.conn = connection
        self.task_id = id
        self.error = None
        self.tr = TaskRepo(self.conn, self.task_id, include_task_packages=False)
        self.sql = tasksql

    def store_sql_error(self, message, severity):
        self.error = build_sql_error_response(message, self, 500, self.DEBUG)
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

    def check_task_id(self):
        self.conn.request_line = self.sql.check_task.format(id=self.task_id)

        status, response = self.conn.send_request()
        if not status:
            self.store_sql_error(response, ll.INFO)
            return False

        if response[0][0] == 0:
            return False
        return True

    def check_params(self, **kwargs):
        pass

    def get(self):
        self.tr.build_task_repo()
        if not self.tr.status:
            return self.tr.error

        repo_pkgs = self.tr.repo['base_repo_pkgs']
        task_add_pkgs = self.tr.repo['task_add_pkgs']
        task_del_pkgs = self.tr.repo['task_del_pkgs']

        self.conn.request_line = self.sql.create_tmp_hshs_table.format(table='tmpRepoHshs')
        status, response = self.conn.send_request()
        if status is False:
            self.store_sql_error(response, ll.ERROR)
            return self.error
        
        self.conn.request_line = (
            self.sql.insert_into_tmp_hshs_table.format(table='tmpRepoHshs'),
            ({'pkghash': _} for _ in repo_pkgs)
        )
        status, response = self.conn.send_request()
        if status is False:
            self.store_sql_error(response, ll.ERROR)
            return self.error

        result_dict = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))

        if task_del_pkgs:
            # create tmp table with task del packages hashes
            self.conn.request_line = self.sql.create_tmp_hshs_table.format(table='tmpTaskDelHshs')
            status, response = self.conn.send_request()
            if status is False:
                self.store_sql_error(response, ll.ERROR)
                return self.error
            
            self.conn.request_line = (
                self.sql.insert_into_tmp_hshs_table.format(table='tmpTaskDelHshs'),
                ({'pkghash': _} for _ in task_del_pkgs)
            )
            status, response = self.conn.send_request()
            if status is False:
                self.store_sql_error(response, ll.ERROR)
                return self.error

            self.conn.request_line = self.sql.diff_packages_by_hshs.format(table='tmpTaskDelHshs')
            status, response = self.conn.send_request()
            if status is False:
                self.store_sql_error(response, ll.ERROR)
                return self.error

            if response:
                for el in response:
                    if el[2].endswith('.src.rpm'):
                        result_dict['src'][el[0]]['del'].append(el[2])
                    else:
                        result_dict[el[1]][el[0]]['del'].append(el[2])

        if task_add_pkgs:
            # create tmp table with task add packages hashes
            self.conn.request_line = self.sql.create_tmp_hshs_table.format(table='tmpTaskAddHshs')
            status, response = self.conn.send_request()
            if status is False:
                self.store_sql_error(response, ll.ERROR)
                return self.error
            
            self.conn.request_line = (
                self.sql.insert_into_tmp_hshs_table.format(table='tmpTaskAddHshs'),
                ({'pkghash': _} for _ in task_add_pkgs)
            )
            status, response = self.conn.send_request()
            if status is False:
                self.store_sql_error(response, ll.ERROR)
                return self.error

            self.conn.request_line = self.sql.diff_packages_by_hshs.format(table='tmpTaskAddHshs')
            status, response = self.conn.send_request()
            if status is False:
                self.store_sql_error(response, ll.ERROR)
                return self.error

            if response:
                for el in response:
                    if el[2].endswith('.src.rpm'):
                        result_dict['src'][el[0]]['add'].append(el[2])
                    else:
                        result_dict[el[1]][el[0]]['add'].append(el[2])

        if task_add_pkgs:
            self.conn.request_line = self.sql.diff_repo_pkgs.format(
                tmp_table1='tmpRepoHshs',
                tmp_table2='tmpTaskAddHshs'
            )
            status, response = self.conn.send_request()
            if status is False:
                self.store_sql_error(response, ll.ERROR)
                return self.error

            if not response:
                self.store_sql_error(f"Failed to get packages add contents for task {self.task_id}", ll.ERROR)
                return self.error

            repo_pkgs_filtered = join_tuples(response)

            self.conn.request_line = self.sql.truncate_tmp_table.format(table='tmpRepoHshs')
            status, response = self.conn.send_request()
            if status is False:
                self.store_sql_error(response, ll.ERROR)
                return self.error

            self.conn.request_line = (
                self.sql.insert_into_tmp_hshs_table.format(table='tmpRepoHshs'),
                ({'pkghash': _} for _ in repo_pkgs_filtered)
            )
            status, response = self.conn.send_request()
            if status is False:
                self.store_sql_error(response, ll.ERROR)
                return self.error

            self.conn.request_line = self.sql.diff_depends_by_hshs.format(table='tmpRepoHshs')
            status, response = self.conn.send_request()
            if status is False:
                self.store_sql_error(response, ll.ERROR)
                return self.error

            repo_deps = response

            self.conn.request_line = self.sql.diff_depends_by_hshs.format(table='tmpTaskAddHshs')
            status, response = self.conn.send_request()
            if status is False:
                self.store_sql_error(response, ll.ERROR)
                return self.error

            task_deps = response

            uniq_repo_pkgs = remove_duplicate([i[0] for i in repo_deps])

            base_struct = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
            for pkg in uniq_repo_pkgs:
                for type_ in ['provide', 'require', 'obsolete', 'conflict']:
                    for arch in lut.default_archs:
                        base_struct[pkg][type_][arch] = []

            def create_struct(deps):
                struct = deepcopy(base_struct)
                [struct[el[0]][el[1]][el[2]].__iadd__(el[3])
                for el in deps if el[0] in base_struct]
                return struct

            task_struct = create_struct(task_deps)
            repo_struct = create_struct(repo_deps)

            for name, type_dict in task_struct.items():
                for type_, arch_dict in type_dict.items():
                    for arch, value in arch_dict.items():
                        task_set = set(value)
                        repo_set = set(repo_struct[name][type_][arch])

                        res_list_del = [dep for dep in repo_set - task_set]
                        res_list_add = [dep for dep in task_set - repo_set]

                        if res_list_del or res_list_add:
                            result_dict[arch][name]['deps'] = []
                            result_dict[arch][name]['deps'].append(
                                {
                                    'type': type_,
                                    'del': res_list_del,
                                    'add': res_list_add
                                }
                            )

        result_dict_2 = {
            'task_id': self.task_id,
            'task_diff': []
        }

        for k, v in result_dict.items():
            arch_dict = {
                'arch': k,
                'packages': []
            }
            for pkg, val in v.items():
                arch_dict['packages'].append(
                    {
                        'package': pkg,
                        'del': val['del'],
                        'add': val['add'],
                        'dependencies': val['deps']
                    }

                )
            result_dict_2['task_diff'].append(arch_dict)

        return result_dict_2, 200
