from utils import get_logger, build_sql_error_response, mmhash
from utils import join_tuples, logger_level as ll
from database.task_sql import tasksql
from collections import defaultdict
from settings import namespace as settings

logger = get_logger(__name__)

class TaskRepo:
    DEBUG = settings.SQL_DEBUG

    def __init__(self, connection, id, include_task_packages):
        self.conn = connection
        self.task_id = id
        self.include_task_packages = include_task_packages
        self.status = False
        self.error = None
        self.repo = {}
        self.sql = tasksql

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

    def _store_sql_error(self, message, severity):
        self.error = build_sql_error_response(message, self, 500, self.DEBUG)
        self.status = False
        self._log_error(severity)

    def check_task_id(self):
        self.conn.request_line = self.sql.check_task.format(id=self.task_id)

        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, ll.INFO)
            return False

        if response[0][0] == 0:
            return False
        return True

    def check_params(self, **kwargs):
        pass

    def build_task_repo(self):
        if not self.check_task_id():
            self._store_sql_error({"Error": f"Non-existent task {self.task_id}"}, ll.ERROR)
            return self.repo

        self.conn.request_line = self.sql.task_repo.format(id=self.task_id)

        status, response = self.conn.send_request()
        if status is False:
            self._store_sql_error(response, ll.ERROR)
            return self.repo

        if not response:
            self._store_sql_error({"Error": f"Non-existent data for task {self.task_id}"}, ll.ERROR)
            return self.repo

        task_repo = response[0][0]

        self.conn.request_line = self.sql.repo_task_content.format(id=self.task_id)

        status, response = self.conn.send_request()
        if status is False:
            self._store_sql_error(response, ll.ERROR)
            return self.repo
        
        if not response:
            self._store_sql_error({"Error": f"Non-existent data for task {self.task_id}"}, ll.ERROR)
            return self.repo

        task_archs = set(('src', 'noarch', 'x86_64-i586'))
        task_try = 0
        task_iter = 0
        for el in response:
            task_archs.add(el[0])
            task_try = el[1]
            task_iter = el[2]

        task_tplan_hashes = set()
        for arch in task_archs:
            t = str(self.task_id) + str(task_try) + str(task_iter) + arch
            task_tplan_hashes.add(mmhash(t))

        self.conn.request_line = (
            self.sql.repo_single_task_plan_hshs, {'hshs': tuple(task_tplan_hashes), 'act': 'add'}
        )

        status, response = self.conn.send_request()
        if status is False:
            self._store_sql_error(response, ll.ERROR)
            return self.repo

        if response:
            task_add_pkgs = set(join_tuples(response))
        else:
            task_add_pkgs = set()

        self.conn.request_line = (
            self.sql.repo_single_task_plan_hshs, {'hshs': tuple(task_tplan_hashes), 'act': 'delete'}
        )

        status, response = self.conn.send_request()
        if status is False:
            self._store_sql_error(response, ll.ERROR)
            return self.repo

        if response:
            task_del_pkgs = set(join_tuples(response))
        else:
            task_del_pkgs = set()

        self.conn.request_line = self.sql.repo_tasks_diff_list.format(id=self.task_id, repo=task_repo)

        status, response = self.conn.send_request()
        if status is False:
            self._store_sql_error(response, ll.ERROR)
            return self.repo

        tasks_diff_list = []
        if response:
            tasks_diff_list += {_[0] for _ in response}

        self.conn.request_line = self.sql.repo_last_repo.format(id=self.task_id, repo=task_repo)

        status, response = self.conn.send_request()
        if status is False:
            self._store_sql_error(response, ll.ERROR)
            return self.repo

        if not response:
            self._store_sql_error(f"Failed to get last repo packages for task {self.task_id}", ll.ERROR)
            return self.repo

        last_repo_pkgs = set(join_tuples(response))

        self.conn.request_line = self.sql.repo_last_repo_content.format(id=self.task_id, repo=task_repo)

        status, response = self.conn.send_request()
        if status is False:
            self._store_sql_error(response, ll.ERROR)
            return self.repo

        if not response:
            self._store_sql_error(f"Failed to get last repo contents for task {self.task_id}", ll.ERROR)
            return self.repo

        last_repo_contents = response[0]

        if tasks_diff_list:
            self.conn.request_line = (
                self.sql.repo_tasks_plan_hshs, {'id': tuple(tasks_diff_list), 'act': 'add'}
            )

            status, response = self.conn.send_request()
            if status is False:
                self._store_sql_error(response, ll.ERROR)
                return self.repo

            if not response:
                tasks_diff_add_hshs = set()
            else:
                tasks_diff_add_hshs = set(join_tuples(response))

            self.conn.request_line = (
                self.sql.repo_tasks_plan_hshs, {'id': tuple(tasks_diff_list), 'act': 'delete'}
            )

            status, response = self.conn.send_request()
            if status is False:
                self._store_sql_error(response, ll.ERROR)
                return self.repo

            if not response:
                tasks_diff_del_hshs = set()
            else:
                tasks_diff_del_hshs = set(join_tuples(response))

            if not tasks_diff_add_hshs and not tasks_diff_del_hshs:
                self._store_sql_error(f"Failed to get task plan hashes for tasks {tasks_diff_list}", ll.ERROR)
                return self.repo
        else:
            tasks_diff_add_hshs = set()
            tasks_diff_del_hshs = set()

        task_base_repo_pkgs = (last_repo_pkgs - tasks_diff_del_hshs) | tasks_diff_add_hshs
        task_current_repo_pkgs = (task_base_repo_pkgs - task_del_pkgs) | task_add_pkgs

        self.repo = {
            'base_repo_pkgs': tuple(task_base_repo_pkgs),
            'task_repo_pkgs': tuple(task_current_repo_pkgs),
            'task_add_pkgs': tuple(task_add_pkgs),
            'task_del_pkgs': tuple(task_del_pkgs),
            # 'last_repo_pkgs': tuple(last_repo_pkgs),
            'last_repo_contents': last_repo_contents,
            'tasks_diff_list': list(tasks_diff_list),
            # 'tasks_diff_add_hshs': tuple(tasks_diff_add_hshs),
            # 'tasks_diff_del_hshs': tuple(tasks_diff_add_hshs)
        }
        self.status = True

    def get(self):
        self.build_task_repo()

        if not self.status:
            return self.error
        
        # create temporary table for packages hashaes
        self.conn.request_line = self.sql.create_tmp_hshs_table.format(table='tmpPkgHshs')
        status, response = self.conn.send_request()
        if status is False:
            self._store_sql_error(response, ll.ERROR)
            return self.error

        # insert hashes for packages into temporary table
        if self.include_task_packages:
            # use task_current_repo_pkgs
            self.conn.request_line = (
                self.sql.insert_into_tmp_hshs_table.format(table='tmpPkgHshs'),
                ({'pkghash': _} for _ in self.repo['task_repo_pkgs'])
            )
        else:
            # use task_base_repo_pkgs
            self.conn.request_line = (
                self.sql.insert_into_tmp_hshs_table.format(table='tmpPkgHshs'),
                ({'pkghash': _} for _ in self.repo['base_repo_pkgs'])
            )
        
        status, response = self.conn.send_request()
        if status is False:
            self._store_sql_error(response, ll.ERROR)
            return self.error

        self.conn.request_line = self.sql.repo_packages_by_hshs.format(table='tmpPkgHshs')

        status, response = self.conn.send_request()
        if status is False:
            self._store_sql_error(response, ll.ERROR)
            return self.error

        if not response:
            if not response:
                self._store_sql_error({"Error": "Failed to get packages data from database"}, ll.ERROR)
                return self.error
        else:
            repo_pkgs = defaultdict(list)
            for el in response:
                if el[5] == 1:
                    repo_pkgs['SRPM'].append(
                        {
                            'name': el[0],
                            'version': el[1],
                            'release': el[2],
                            'filename': el[4]
                        }
                    )
                else:
                    repo_pkgs[el[3]].append(
                        {
                            'name': el[0],
                            'version': el[1],
                            'release': el[2],
                            'filename': el[4]
                        }
                    )

        # build final result
        res = {
            'task_id': self.task_id,
            'base_repository': {
                'name': self.repo['last_repo_contents'][0],
                'date': self.repo['last_repo_contents'][1].isoformat(),
                'tag': self.repo['last_repo_contents'][2]
            },
            'task_diff_list': self.repo['tasks_diff_list'],
            'archs': []
        }

        for k, v in repo_pkgs.items():
            res['archs'].append(
                {
                    'arch': k,
                    'packages': v
                }
            )

        return res, 200
