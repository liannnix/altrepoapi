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

    check_task = """
SELECT count(task_id)
FROM TaskStates
WHERE task_id = {id}
"""

    get_last_tasks_from_progress = """
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
        TT.stage AS task_stage,
        argMax(task_depends, ts) AS depends
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

    get_subtasks_from_progress = """
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
WHERE (task_id IN (SELECT task_id FROM {tmp_table}))
    AND (type != 'progress')
GROUP BY
    task_id,
    subtask_id
ORDER BY subtask_id ASC
"""

    get_subtasks_status_from_progress = """
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

    get_all_tasks_branches = """
SELECT groupUniqArray(task_repo) FROM TaskProgress
"""

    get_task_approval = """
SELECT DISTINCT
    task_id,
    tapp_type,
    tapp_name
FROM
(
    SELECT task_id,
           subtask_id,
           tapp_type,
           tapp_name,
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
    GROUP BY task_id, subtask_id, tapp_type, tapp_name
)
WHERE task_id IN (SELECT task_id FROM {tmp_table})
    AND revoked = 0
"""

    get_subtask_approval = """
SELECT DISTINCT
    task_id,
    subtask_id,
    groupUniqArray((tapp_type, tapp_name, tapp_message))
FROM
(
    SELECT task_id,
           subtask_id,
           tapp_type,
           tapp_name,
           tapp_message,
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
    GROUP BY task_id, subtask_id, tapp_type, tapp_name, tapp_message
)
WHERE task_id IN (SELECT task_id FROM {tmp_table})
    AND revoked = 0
group by task_id,
         subtask_id
"""

    task_global_search_fast = """
SELECT * FROM (
    SELECT
        argMax(search_string, ts) AS search,
        lead
    FROM GlobalSearch
    {where}
    GROUP BY lead
    ORDER BY max(ts) DESC
)
{where2}
{limit}
"""

    find_tasks = """
SELECT
    task_id,
    SS[1] AS repo,
    SS[2] AS owner,
    SS[4] AS state,
    ts
FROM (
    SELECT
        task_id,
        arraySlice(
            splitByChar('|', search),
            1,
            4
        ) AS SS,
        ts_ AS ts
    FROM (
        SELECT
            toUInt32(lead) AS task_id,
            argMax(search_string, ts) AS search,
            max(ts) AS ts_
        FROM GlobalSearch
        {where}
        GROUP BY lead
        ORDER BY max(ts) DESC
    )
    {where2}
    {limit}
)
"""

    get_tasks_meta = """
SELECT
    task_id,
    argMax(try, changed) AS try,
    argMax(iter, changed) AS iter,
    argMax(message, changed) AS message,
    max(changed) AS task_changed,
    argMax(task_stage, changed) AS stage,
    argMax(depends, changed) AS depends
FROM (
    SELECT
        task_id,
        argMax(task_state, ts) AS state,
        argMax(task_try, ts) AS try,
        argMax(task_iter, ts) AS iter,
        argMax(task_message, ts) AS message,
        argMax(task_changed, ts) AS changed,
        argMax(task_depends, ts) AS depends,
        TT.stage as task_stage
    FROM TaskProgress
    LEFT JOIN (
        SELECT task_id, argMax(stage, ts) AS stage
        FROM TaskProgress
        WHERE stage_status = 'started'
            AND task_state = 'BUILDING'
            AND task_id IN (SELECT * FROM {tmp_table})
        GROUP BY task_id
        ) AS TT ON TT.task_id = TaskProgress.task_id
    WHERE type = 'state'
        AND task_id IN (SELECT * FROM {tmp_table})
    GROUP BY task_id, task_stage
    UNION ALL
    SELECT
        task_id,
        argMax(task_state, task_changed) AS state,
        TI.try AS try,
        TI.iter AS iter,
        argMax(task_message, task_changed) AS message,
        max(task_changed) as changed,
        argMax(task_depends, task_changed) AS depends,
        '' as task_stage
    FROM TaskStates
    LEFT JOIN (
        SELECT
            task_id,
            argMax(task_try, task_changed) AS try,
            argMax(task_iter, task_changed) AS iter
        FROM TaskIterations
        WHERE task_id IN (SELECT * FROM {tmp_table})
        GROUP BY task_id
        ) AS TI ON TI.task_id = TaskStates.task_id
    WHERE task_id IN (SELECT * FROM {tmp_table})
    GROUP BY task_id, try, iter
)
GROUP BY task_id ORDER BY task_changed DESC
"""

    get_task_subtasks = """
WITH
tasks_in_progress AS (
    SELECT DISTINCT task_id FROM TaskProgress
    WHERE task_id IN {tmp_table}
),
tasks_not_in_progress AS (
    SELECT DISTINCT task_id FROM Tasks
    WHERE task_id IN {tmp_table}
        AND task_id NOT IN tasks_in_progress
)
SELECT
    task_id,
    subtask_id,
    argMax(sub_type, changed),
    argMax(srpm, changed),
    argMax(srpm_name, changed),
    argMax(srpm_evr, changed),
    argMax(dir, changed),
    argMax(tag_id, changed),
    argMax(tag_name, changed),
    argMax(tag_author, changed),
    argMax(package, changed),
    argMax(pkg_from, changed),
    max(changed),
    argMax(tp, changed)
FROM (
    SELECT * FROM (
        SELECT
            task_id,
            subtask_id,
            argMax(subtask_type, ts) AS sub_type,
            argMax(subtask_srpm, ts) AS srpm,
            argMax(subtask_srpm_name, ts) AS srpm_name,
            argMax(subtask_srpm_evr, ts) AS srpm_evr,
            argMax(subtask_dir, ts) AS dir,
            argMax(subtask_tag_id, ts) AS tag_id,
            argMax(subtask_tag_name, ts) AS tag_name,
            argMax(subtask_tag_author, ts) AS tag_author,
            argMax(subtask_package, ts) AS package,
            argMax(subtask_pkg_from, ts) AS pkg_from,
            argMax(subtask_changed, ts) AS changed,
            argMax(type, ts) AS tp
        FROM TaskSubtaskProgress
        WHERE (task_id in tasks_in_progress)
            AND (type != 'progress')
        GROUP BY
            task_id,
            subtask_id
    ) WHERE sub_type != 'unknown'
    ORDER BY subtask_id ASC
    UNION ALL
    SELECT * FROM (
        SELECT
            task_id,
            subtask_id,
            argMax(subtask_type, ts) AS sub_type,
            argMax(subtask_srpm, ts) AS srpm,
            argMax(subtask_srpm_name, ts) AS srpm_name,
            argMax(subtask_srpm_evr, ts) AS srpm_evr,
            argMax(subtask_dir, ts) AS dir,
            argMax(subtask_tag_id, ts) AS tag_id,
            argMax(subtask_tag_name, ts) AS tag_name,
            argMax(subtask_tag_author, ts) AS tag_author,
            argMax(subtask_package, ts) AS package,
            argMax(subtask_pkg_from, ts) AS pkg_from,
            argMax(subtask_changed, ts) AS changed,
            if(has(groupUniqArray(subtask_deleted), 0), 'create', 'delete') AS tp
        FROM Tasks
        WHERE task_id IN tasks_not_in_progress
        GROUP BY task_id, subtask_id
    ) WHERE sub_type != 'unknown'
)
GROUP BY task_id, subtask_id
ORDER BY subtask_id
"""

    get_task_table = """
SELECT
    'progress' AS table,
    any(task_id) AS id,
    argMax(task_state, ts) AS state,
    max(ts) AS changed
FROM TaskProgress
WHERE task_id = {id}
UNION ALL
SELECT
    'state' AS table,
    any(task_id) AS id,
    argMax(task_state, task_changed) AS state,
    max(task_changed) AS changed
FROM TaskStates
WHERE task_id = {id}
"""

    get_task_info_from_progress = """
SELECT
    task_id,
    argMax(task_repo, ts) AS branch,
    argMax(task_state, ts) AS state,
    argMax(task_owner, ts) AS owner,
    argMax(task_try, ts) AS try,
    argMax(task_iter, ts) AS iter,
    argMax(task_changed, ts) AS changed,
    argMax(task_message, ts) AS message,
    TT.stage AS task_stage,
    argMax(task_depends, ts) AS depends,
    TT.iters AS task_iters
FROM TaskProgress
LEFT JOIN (
    SELECT task_id, argMax(stage, ts) AS stage, TI.prev_iter as iters
    FROM TaskProgress
    LEFT JOIN (
        SELECT task_id, groupUniqArray((task_try, task_iter)) AS prev_iter
        FROM TaskProgress
        WHERE task_try != 0
            AND task_id = {id}
        GROUP BY task_id
    ) AS TI ON TI.task_id = TaskProgress.task_id
    WHERE stage_status = 'started'
        AND task_state = 'BUILDING'
        AND task_id = {id}
    GROUP BY task_id, iters
    ) AS TT ON TT.task_id = TaskProgress.task_id
WHERE type = 'state'
    AND task_id = {id}
GROUP BY task_id, task_stage, task_iters
"""

    get_task_info_from_state = """
WITH
t_state AS (
    SELECT
        any(task_id) AS t_id,
        max(task_changed) AS changed,
        argMax(task_state, task_changed) AS state,
        argMax(task_depends, task_changed) AS depends,
        argMax(task_message, task_changed) AS message
    FROM TaskStates
    WHERE task_id = {id}
)
SELECT
    task_id,
    repo,
    state,
    owner,
    try,
    iter,
    changed,
    message,
    '' AS stage,
    depends,
    task_iters
FROM (
    SELECT
        t_id AS task_id,
        state,
        changed,
        message,
        depends,
        TI.repo,
        TI.owner
    FROM t_state
    LEFT JOIN (
        SELECT
        task_id,
        any(task_repo) AS repo,
        any(task_owner) AS owner
    FROM Tasks
    WHERE subtask_deleted = 0
        AND (task_id, task_changed) = (SELECT t_id, changed FROM t_state)
    GROUP BY task_id
    ) AS TI USING task_id
) AS TS
LEFT JOIN (
    SELECT
        any(task_id) AS t_id,
        argMax(task_try, task_changed) AS try,
        argMax(task_iter, task_changed) AS iter,
        groupUniqArray((task_try, task_iter)) AS task_iters
    FROM TaskIterations
    WHERE task_id = {id}
) AS TT ON TS.task_id = TT.t_id
"""

    get_subtasks_by_id_from_progress = """
 SELECT * FROM (
    SELECT
        task_id,
        subtask_id,
        argMax(subtask_type, ts) AS sub_type,
        argMax(subtask_srpm, ts) AS srpm,
        argMax(subtask_srpm_name, ts) AS srpm_name,
        argMax(subtask_srpm_evr, ts) AS srpm_evr,
        argMax(subtask_dir, ts) AS dir,
        argMax(subtask_tag_id, ts) AS tag_id,
        argMax(subtask_tag_name, ts) AS tag_name,
        argMax(subtask_tag_author, ts) AS tag_author,
        argMax(subtask_package, ts) AS package,
        argMax(subtask_pkg_from, ts) AS pkg_from,
        argMax(subtask_changed, ts) AS changed,
        argMax(type, ts) AS tp
    FROM TaskSubtaskProgress
    WHERE (task_id = {id})
        AND (type != 'progress')
    GROUP BY
        task_id,
        subtask_id
) WHERE sub_type != 'unknown'
ORDER BY subtask_id ASC
"""

    get_subtasks_by_id_from_state = """
SELECT * FROM (
    SELECT
        task_id,
        subtask_id,
        argMax(subtask_type, ts) AS sub_type,
        argMax(subtask_srpm, ts) AS srpm,
        argMax(subtask_srpm_name, ts) AS srpm_name,
        argMax(subtask_srpm_evr, ts) AS srpm_evr,
        argMax(subtask_dir, ts) AS dir,
        argMax(subtask_tag_id, ts) AS tag_id,
        argMax(subtask_tag_name, ts) AS tag_name,
        argMax(subtask_tag_author, ts) AS tag_author,
        argMax(subtask_package, ts) AS package,
        argMax(subtask_pkg_from, ts) AS pkg_from,
        argMax(subtask_changed, ts) AS changed,
        if(has(groupUniqArray(subtask_deleted), 0), 'create', 'delete') AS tp
    FROM Tasks
    WHERE (task_id = {id})
    GROUP BY task_id, subtask_id
) WHERE sub_type != 'unknown'
ORDER BY subtask_id
"""

    get_subtasks_status_by_id_from_progress = """
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
    WHERE task_id = {id}
        AND subtask_id IN {sub_ids}
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

    get_subtasks_status_by_id_from_state = """
SELECT
    task_id,
    subtask_id,
    groupUniqArray((subtask_arch, status)),
    'progress' as stype
FROM (
      SELECT
        task_id,
        subtask_id,
        subtask_arch,
        argMax(titer_status, task_changed) as status
    FROM TaskIterations
    WHERE task_id = {id}
        AND subtask_id IN (
            SELECT subtask_id
            FROM (
                 SELECT subtask_id,
                        argMax(subtask_deleted, task_changed) AS subdel
                 FROM Tasks
                 WHERE task_id = {id}
                       AND subtask_id IN {sub_ids}
                 GROUP BY subtask_id
            ) WHERE subdel = 0
        )
    GROUP BY
        task_id,
        subtask_id,
        subtask_arch
)
GROUP BY
    task_id,
    subtask_id,
    stype
"""


sql = SQL()
