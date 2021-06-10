from utils import get_logger, build_sql_error_response, tuplelist_to_dict, convert_to_dict
from database.task_sql import SQL as sql

from operator import itemgetter

logger = get_logger(__name__)
class TaskInfo():
    """Get information about the task based on task ID
    Otpionally uses task try and iteration parameters

    Returns:
        tuple(dict, int): retrun task information or error (if occures) and http response code (200, 400, 404, 500)
    """
    DEBUG = True

    def __init__(self, connection, id_, try_, iter_) -> None:
        self.conn = connection
        self.task_id = id_
        self.task_try = try_
        self.task_iter = iter_

    def check_task_id(self):
        self.conn.request_line = sql.check_task.format(id=self.task_id)

        status, response = self.conn.send_request()
        if not status:
            return build_sql_error_response(response, self, 500)
        
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
        if self.task_try is not None and self.task_iter is not None:
            try_iteration = (self.task_try, self.task_iter)
        else:
            try_iteration = None

        self.conn.request_line = sql.get_task_info.format(id=self.task_id)

        status, response = self.conn.send_request()
        if not status:
            return build_sql_error_response(response, self, 500, self.DEBUG)
        
        if not response:
            return build_sql_error_response(
                {"Error": f"No data found in database for task '{self.task_id}'"},
                self, 404, self.DEBUG
            )

        branch, user_id = response[0][1], response[0][2]
        all_rebuilds = [i[0] for i in response]

        self.conn.request_line = sql.get_task_content.format(id=self.task_id)
        if try_iteration:
            self.conn.request_line = sql.get_task_content_rebuild.format(
                id=self.task_id, ti=try_iteration)

        status, response = self.conn.send_request()
        if not status:
            return build_sql_error_response(response, self, 500, self.DEBUG)
        
        if not response:
            return build_sql_error_response(
                {"Error": f"No data found in database for task '{self.task_id}' with rebuild '{try_iteration}'"},
                self, 404, self.DEBUG
            )

        src_pkgs = response

        task_status = src_pkgs[0][1]
        task_message = src_pkgs[0][5]
        try_iteration = src_pkgs[0][3]
        pkg_subtask = {pkg[0]: pkg[2] for pkg in src_pkgs}

        pkg_hshs = [val for sublist in [[i[0]] + i[4] for i in response]
                    for val in sublist]

        self.conn.request_line = sql.get_packages_info.format(hshs=tuple(pkg_hshs))
        
        status, response = self.conn.send_request()
        if not status:
            return build_sql_error_response(response, self, 500, self.DEBUG)
        
        name_hsh = tuplelist_to_dict(response, 5)

        self.conn.request_line = sql.get_task_approvals.format(id=self.task_id)
        
        status, response = self.conn.send_request()
        if not status:
            return build_sql_error_response(response, self, 500, self.DEBUG)
        
        if not response:
            for hsh, subtask in pkg_subtask.items():
                pkg_subtask[hsh] = [pkg_subtask[hsh]] + ['', '']
        else:
            task_approvals = tuplelist_to_dict([_[0] for _ in response], 4)
            for hsh, subtask in pkg_subtask.items():
                result_list = ['', '']
                if subtask in task_approvals:
                    if task_approvals[subtask][1] == 'approve':
                        result_list[0] = task_approvals[subtask]
                    else:
                        result_list[1] = task_approvals[subtask]
                pkg_subtask[hsh] = [pkg_subtask[hsh]] + result_list

        beehive_result = ""

        result_list = []
        for pkg in src_pkgs:
            res = [
                *name_hsh[pkg[0]][:-2],
                branch,
                user_id,
                task_status,
                *pkg_subtask[pkg[0]],
                task_message, 
                try_iteration,
                sorted(all_rebuilds),
                tuplelist_to_dict(
                    [(name_hsh[hsh][3], name_hsh[hsh][0]) for hsh in pkg[4] if hsh != 0], 1
                ),
                name_hsh[pkg[0]][-1],
                beehive_result
            ]
            if res not in result_list:
                result_list.append(res)

        fields = ['src_pkg', 'version', 'release', 'branch', 'user', 'status',
                'subtask', 'approve', 'disapprove', 'task_msg', 'current_rebuild',
                'all_rebuilds', 'subtask_packages', 'description', 'beehive_check']

        res = convert_to_dict(fields, sorted(result_list, key=itemgetter(6)))
        res = [{'task_id': self.task_id,'subtask_id': _['subtask'], 'subtask_contents': _} for _ in res.values()]

        return res, 200
