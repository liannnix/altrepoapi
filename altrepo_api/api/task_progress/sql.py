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
SELECT * FROM (
    SELECT
        task_id,
        argMax(task_repo, ts) AS branch,
        argMax(task_state, ts) AS state,
        argMax(task_owner, ts) AS owner,
        argMax(task_try, ts) AS try,
        argMax(task_iter, ts) AS iter,
        argMax(task_changed, ts) AS changed,
        argMax(task_message, ts) AS message,
        TT.stage as task_stage
    FROM TaskProgress
    LEFT JOIN (
        SELECT task_id, argMax(stage, ts) as stage
        FROM TaskProgress
        WHERE stage_status = 'started'
            AND task_state = 'BUILDING'
        GROUP BY task_id
        ) AS TT ON TT.task_id = TaskProgress.task_id
    WHERE type = 'state'
        {branch}
    GROUP BY task_id, task_stage
    ORDER BY changed DESC
) WHERE (state != 'DELETED')
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
    argMax(type, ts)
FROM TaskSubtaskProgress
WHERE (task_id in (SELECT task_id FROM {tmp_table}))
    AND (type != 'progress')
GROUP BY
    task_id,
    subtask_id
ORDER BY subtask_id ASC
"""

    get_subtasks_status = """
SELECT
    task_id,
    subtask_id,
    groupUniqArray((arch, status)),
    stype
FROM
(
    SELECT
        task_id,
        subtask_id,
        arch,
        argMax(stage_status, ts) as status,
        argMax(type, ts) AS stype,
        max(ts) as subts
    FROM TaskSubtaskProgress
    WHERE (task_id, subtask_id) IN (
        SELECT task_id, subtask_id
        FROM {tmp_table}
    )
    GROUP BY
        task_id,
        subtask_id,
        arch
) AS TS
INNER JOIN (
    SELECT
        task_id AS tid,
        max(ts) as building_ts
    FROM TaskProgress
    WHERE task_state = 'BUILDING'
        AND type = 'state'
    GROUP BY task_id
) AS LBTS ON LBTS.tid = TS.task_id
WHERE stype = 'progress'
    AND arch != 'all'
    AND subts >= LBTS.building_ts
GROUP BY
    task_id,
    subtask_id,
    stype
"""

    get_all_pkgset_names = """
SELECT groupUniqArray(task_repo) FROM TaskProgress    
"""

    get_task_approval = """
SELECT DISTINCT
    task_id,
    date,
    type,
    nickname,
    message,
    revoked
FROM
(
    SELECT task_id,
           subtask_id,
           argMax(tapp_date, ts) AS date,
           argMax(tapp_type, ts) as type,
           argMax(tapp_name, ts) AS nickname,
           argMax(tapp_message, ts) AS message,
           argMax(tapp_revoked, ts) AS revoked
    FROM TaskApprovals
    WHERE task_id NOT IN (
        SELECT task_id FROM (
            SELECT task_id, argMax(task_state, task_changed) AS state
            FROM TaskStates
            GROUP BY task_id
        )
        WHERE state = 'DELETED'
    )
    AND (task_id, subtask_id) NOT IN (
        SELECT task_id, subtask_id FROM (
            SELECT task_id,
                   subtask_id,
                   argMax(subtask_deleted, ts) AS sub_del
            FROM Tasks
            GROUP BY task_id, subtask_id
        ) WHERE sub_del = 1
    )
    GROUP BY task_id, subtask_id
)
WHERE task_id in (SELECT task_id FROM {tmp_table})
    AND revoked = 0    
"""

    get_task_dependencies = """
SELECT
    task_id,
    argMax(task_depends, ts)
FROM TaskProgress
WHERE task_state = 'POSTPONED'
    AND task_id IN (SELECT task_id FROM {tmp_table})
GROUP BY task_id
"""


sql = SQL()
