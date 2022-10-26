# ALTRepo API
# Copyright (C) 2021-2022  BaseALT Ltd

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from dataclasses import dataclass


@dataclass(frozen=True)
class SQL:

    get_last_tasks = """
SELECT
    task_id,
    argMax(task_repo, ts) AS branch,
    argMax(task_state, ts) AS state,
    argMax(task_owner, ts) AS owner,
    argMax(task_changed, ts) AS changed,
    argMax(task_message, ts) AS message,
    TT.prev_iter as prev_iter
FROM TaskProgress
LEFT JOIN (
    SELECT task_id, groupUniqArray((task_try, task_iter)) AS prev_iter
    FROM TaskProgress
    WHERE task_try != 0
    GROUP BY task_id
) AS TT ON TT.task_id = TaskProgress.task_id
WHERE type = 'state'
    {branch}
GROUP BY task_id, prev_iter
ORDER BY changed DESC
{limit}
"""

    get_subtasks = """
SELECT
    task_id,
    subtask_id,
    argMax(subtask_type, ts),
    argMax(subtask_srpm, ts),
    argMax(subtask_srpm_name, ts),
    argMax(subtask_srpm_evr, ts),
    argMax(subtask_dir, ts),
    argMax(subtask_tag_id, ts),
    argMax(subtask_tag_name, ts),
    argMax(subtask_tag_author, ts),
    argMax(subtask_package, ts),
    argMax(subtask_pkg_from, ts),
    argMax(subtask_changed, ts),
    argMax(type, ts),
    argMax(stage, ts),
    argMax(stage_status, ts),
    argMax(status, ts)
FROM TaskSubtaskProgress
WHERE (task_id in {tasks}) AND (type != 'progress')
GROUP BY
    task_id,
    subtask_id
ORDER BY subtask_id ASC
"""

    get_subtasks_archs = """
SELECT
    task_id,
    subtask_id,
    groupUniqArray(arch)
FROM TaskSubtaskProgress
WHERE ((task_id, subtask_id) IN {subtasks}) AND (type = 'progress') AND (stage_status IN ('processed', 'failed'))
GROUP BY
    task_id,
    subtask_id
"""


sql = SQL()
