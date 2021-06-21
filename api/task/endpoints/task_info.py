from utils import get_logger, build_sql_error_response
from utils import datetime_to_iso, mmhash, logger_level as ll
from database.task_sql import tasksql
from settings import namespace

from collections import defaultdict

logger = get_logger(__name__)


class Task:
    def __init__(self, connection, id_, try_, iter_, debug_):
        self.conn = connection
        self.sql = tasksql
        self.DEBUG = debug_
        self.status = False
        self.task_id = id_
        self.task = defaultdict(lambda: None, key=None)
        self.task = {
            'id': id_,
            'try': try_,
            'iter': iter_
        }

    def store_sql_error(self, message, severity, http_code):
        self.error = build_sql_error_response(message, self, http_code, self.DEBUG)
        self.status = False
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

    def build_task_state(self):
        if self.task['try'] is not None and self.task['iter'] is not None:
            try_iter = (self.task['try'], self.task['iter'])
        else:
            try_iter = None

        self.conn.request_line = self.sql.task_repo_owner.format(id=self.task_id)
        status, response = self.conn.send_request()
        if not status:
            self.store_sql_error(response, ll.ERROR, 500)
            return {}
        if not response:
            self.store_sql_error(
                {"Error": f"No data found in database for task '{self.task_id}'"},
                ll.INFO, 404
            )
            return {}

        self.task['branch'] = response[0][0] 
        self.task['user'] = response[0][1]

        self.conn.request_line = self.sql.task_all_iterations.format(id=self.task_id)
        status, response = self.conn.send_request()
        if not status:
            self.store_sql_error(response, ll.ERROR, 500)
            return {}
        if not response:
            self.store_sql_error(
                {"Error": f"No data found in database for task '{self.task_id}'"},
                ll.INFO, 404
            )
            return {}

        self.task['rebuilds'] = {(i[0], i[1]): {'subtasks': [], 'changed': i[3]} for i in response}
        for ti in self.task['rebuilds'].keys():
            for el in response:
                if (el[0], el[1]) == ti:
                    self.task['rebuilds'][ti]['subtasks'].append(el[2])
            self.task['rebuilds'][ti]['subtasks'] = sorted(list(set(self.task['rebuilds'][ti]['subtasks'])))

        if try_iter:
            if try_iter not in self.task['rebuilds']:
                self.store_sql_error(
                    {"Error": f"No data found in database for task '{self.task_id}' with rebuild '{try_iter}'"},
                    ll.INFO, 404
                )
                return {}
        else:
            try_iter = max(self.task['rebuilds'])
            self.task['try'], self.task['iter'] = try_iter
        
        task_changed = self.task['rebuilds'][try_iter]['changed']
        self.task['subtasks'] = {_: {} for _ in self.task['rebuilds'][try_iter]['subtasks']}


        self.conn.request_line = self.sql.task_state_by_task_changed.format(
            id=self.task_id, changed=task_changed
        )
        status, response = self.conn.send_request()
        if not status:
            self.store_sql_error(response, ll.ERROR, 500)
            return {}
        if not response:
            self.store_sql_error(
                {"Error": f"No data found in database for task '{self.task_id}' with rebuild '{try_iter}'"},
                ll.INFO, 404
            )
            return {}

        self.task['state_raw'] = dict(zip(self.sql.task_state_keys, response[0]))

        self.conn.request_line = self.sql.task_subtasks_by_task_changed.format(
            id=self.task_id, changed=task_changed
        )
        status, response = self.conn.send_request()
        if not status:
            self.store_sql_error(response, ll.ERROR, 500)
            return {}
        if not response:
            self.store_sql_error(
                {"Error": f"No data found in database for task '{self.task_id}' with rebuild '{try_iter}'"},
                ll.INFO, 404
            )
            return {}

        self.task['subtasks_raw'] = [dict(zip(self.sql.task_subtasks_keys, r)) for r in response]

        self.conn.request_line = self.sql.task_iterations_by_task_changed.format(
            id=self.task_id, changed=task_changed
        )
        status, response = self.conn.send_request()
        if not status:
            self.store_sql_error(response, ll.ERROR, 500)
            return {}
        if not response:
            self.store_sql_error(
                {"Error": f"No data found in database for task '{self.task_id}' with rebuild '{try_iter}'"},
                ll.INFO, 404
            )
            return {}

        self.task['iterations_raw'] = [dict(zip(self.sql.task_iterations_keys, r)) for r in response]

        self.task['subtasks'] = {_['subtask_id']: {} for _ in self.task['subtasks_raw']}

        self.task['archs'] = set(('src', 'noarch', 'x86_64-i586'))
        [self.task['archs'].add(_['subtask_arch']) for _ in self.task['iterations_raw']]
        self.task['archs'] = tuple(self.task['archs'])

        self.task['tplan_hashes'] = {}
        for arch in self.task['archs']:
            t = str(self.task_id) + str(self.task['try']) + str(self.task['iter']) + arch
            self.task['tplan_hashes'][arch] = mmhash(t)

        self.task['plan'] = {
            'add': {'src': {}, 'bin': {}},
            'del': {'src': {}, 'bin': {}},
        }

        self.conn.request_line = self.sql.task_plan_packages.format(
            action='add', hshs=tuple([_ for _ in self.task['tplan_hashes'].values()])
        )
        status, response = self.conn.send_request()
        if not status:
            self.store_sql_error(response, ll.ERROR, 500)
            return {}
        if not response:
            pass

        for el in response:
            if el[6] == 1:
                self.task['plan']['add']['src'][el[0]] = {
                    'name': el[1],
                    'version': el[2],
                    'release': el[3],
                    'filename': el[4],
                    'arch': el[5]
                }
            else:
                self.task['plan']['add']['bin'][el[0]] = {
                    'name': el[1],
                    'version': el[2],
                    'release': el[3],
                    'filename': el[4],
                    'arch': el[5]
                }
        
        self.conn.request_line = self.sql.task_plan_packages.format(
            action='delete', hshs=tuple([_ for _ in self.task['tplan_hashes'].values()])
        )
        status, response = self.conn.send_request()
        if not status:
            self.store_sql_error(response, ll.ERROR, 500)
            return {}
        if not response:
            pass

        for el in response:
            if el[6] == 1:
                self.task['plan']['del']['src'][el[0]] = {
                    'name': el[1],
                    'version': el[2],
                    'release': el[3],
                    'filename': el[4],
                    'arch': el[5]
                }
            else:
                self.task['plan']['del']['bin'][el[0]] = {
                    'name': el[1],
                    'version': el[2],
                    'release': el[3],
                    'filename': el[4],
                    'arch': el[5]
                }

        self.conn.request_line = self.sql.task_approvals.format(id=self.task_id)
        status, response = self.conn.send_request()
        if not status:
            self.store_sql_error(response, ll.ERROR, 500)
            return {}

        for subtask in self.task['subtasks']:
            self.task['subtasks'][subtask].update({'approvals': []})
        if response:
            task_approvals = []
            tapp_keys = ('id', 'date', 'type', 'name', 'message', 'revoked')
            for i in range(len(response)):
                task_approvals.append(
                    dict([(tapp_keys[j], response[i][0][j]) for j in range(len(response[i][0]))])
                )

            for subtask in self.task['subtasks']:
                self.task['subtasks'][subtask]['approvals'] = [_ for _ in task_approvals if _['id'] == subtask]
                for tapp in self.task['subtasks'][subtask]['approvals']:
                    tapp['date'] = datetime_to_iso(tapp['date'])

        self.task['state'] = self.task['state_raw']['task_state']
        self.task['runby'] = self.task['state_raw']['task_runby']
        self.task['depends'] = self.task['state_raw']['task_depends']
        self.task['testonly'] = self.task['state_raw']['task_testonly']
        self.task['failearly'] = self.task['state_raw']['task_failearly']
        self.task['shared'] = self.task['state_raw']['task_shared']
        self.task['message'] = self.task['state_raw']['task_message']
        self.task['version'] = self.task['state_raw']['task_version']
        self.task['prev'] = self.task['state_raw']['task_prev']
        self.task['last_changed'] = datetime_to_iso(self.task['state_raw']['task_changed'])

        for subtask in self.task['subtasks'].keys():
            contents = {'archs': []}
            for sub_ in self.task['subtasks_raw']:
                if sub_['subtask_id'] == subtask:
                    contents['last_changed'] = datetime_to_iso(sub_['subtask_changed'])
                    contents['userid'] = sub_['subtask_userid']
                    contents['dir'] = sub_['subtask_dir']
                    contents['package'] = sub_['subtask_package']
                    contents['type'] = sub_['subtask_type']
                    contents['pkg_from'] = sub_['subtask_pkg_from']
                    contents['sid'] = sub_['subtask_sid']
                    contents['tag_author'] = sub_['subtask_tag_author']
                    contents['tag_id'] = sub_['subtask_tag_id']
                    contents['tag_name'] = sub_['subtask_tag_name']
                    contents['srpm'] = sub_['subtask_srpm']
                    contents['srpm_name'] = sub_['subtask_srpm_name']
                    contents['srpm_evr'] = sub_['subtask_srpm_evr']
                    break
            for iter_ in self.task['iterations_raw']:
                if iter_['subtask_id'] == subtask and iter_['subtask_arch'] == 'x86_64':
                    if iter_['titer_srcrpm_hash'] != 0 and iter_['titer_srcrpm_hash'] in self.task['plan']['add']['src']:
                        contents['source_package'] = self.task['plan']['add']['src'][iter_['titer_srcrpm_hash']]
                    else:
                        contents['source_package'] = {}
                    break
            for iter_ in self.task['iterations_raw']:
                if iter_['subtask_id'] == subtask:
                    iteration = {}
                    iteration['last_changed'] = datetime_to_iso(iter_['titer_ts'])
                    iteration['arch'] = iter_['subtask_arch']
                    iteration['status'] = iter_['titer_status']
                    contents['archs'].append(iteration)
                    
            self.task['subtasks'][subtask].update(contents)

        self.task['all_rebuilds'] = [(str(_[0]) + '.' + str(_[1])) for _ in sorted(self.task['rebuilds'].keys())]

        self.status = True
        return self.task
        

class TaskInfo:
    """Get information about the task based on task ID
    Otpionally uses task try and iteration parameters

    Returns:
        tuple(dict, int): retrun task information or error (if occured) and http response code (200, 400, 404, 500)
    """
    DEBUG = namespace.SQL_DEBUG

    def __init__(self, connection, id_, try_, iter_) -> None:
        self.conn = connection
        self.task_id = id_
        self.task_try = try_
        self.task_iter = iter_
        self.sql = tasksql
        self.task = Task(self.conn, self.task_id, self.task_try, self.task_iter, self.DEBUG)

    def check_task_id(self):
        self.conn.request_line = self.sql.check_task.format(id=self.task_id)

        status, response = self.conn.send_request()
        if not status:
            logger.error(build_sql_error_response(response, self, 500, self.DEBUG))
            return False

        if response[0][0] == 0:
            return False
        return True

    def check_params(self):
        if self.task_try is not None and self.task_iter is not None:
            if self.task_try > 0 and self.task_iter > 0:
                return True
            else:
                return False
        elif self.task_try is None and self.task_iter is None:
            return True
        else:
            return False

    def get(self):
        res = self.task.build_task_state()

        if self.task.status:
            res['rebuilds'] = res['all_rebuilds']

            subtasks = []
            for subtask, contents in res['subtasks'].items():
                subtask_dict = {'subtask_id': subtask}
                subtask_dict.update(contents)
                subtasks.append(subtask_dict)
            res['subtasks'] = subtasks

            res['plan']['add']['src'] = [_ for _ in res['plan']['add']['src'].values()]
            res['plan']['add']['bin'] = [_ for _ in res['plan']['add']['bin'].values()]
            res['plan']['del']['src'] = [_ for _ in res['plan']['del']['src'].values()]
            res['plan']['del']['bin'] = [_ for _ in res['plan']['del']['bin'].values()]
            
            return res, 200
        else:
            return self.task.error 
