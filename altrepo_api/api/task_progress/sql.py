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

    get_all_pkgset_names = """
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

    get_task_dependencies_from_progress = """
SELECT
    task_id,
    argMax(task_depends, ts)
FROM TaskProgress
WHERE task_state = 'POSTPONED'
    AND task_id IN (SELECT task_id FROM {tmp_table})
GROUP BY task_id
"""

    task_search_fast_lookup = """
SELECT * FROM (
    SELECT
        task_id,
        any(owner),
        any(repo),
        argMax(state, TS) AS state,
        groupArray(package),
        max(TS) AS ts
    FROM
    (
        SELECT
            task_id,
            subtask_id,
            any(task_repo) AS repo,
            any(task_owner) AS owner,
            any(subtask_package) AS package,
            argMax(task_state, ts) AS state,
            argMax(is_deleted, ts) AS deleted,
            max(ts) AS TS
        FROM TasksSearch
        WHERE task_id IN (
            SELECT DISTINCT task_id
            FROM TasksSearch
            WHERE {where}
            {branch}
            {owner}
        )
        GROUP BY
            task_id,
            subtask_id
    )
    WHERE (subtask_id = 0) OR (deleted = 0)
    GROUP BY task_id
    ORDER BY ts DESC
)
WHERE state != 'DELETED'
{limit}
"""

    find_all_tasks = """
WITH task_search AS (
    SELECT * FROM (
        SELECT task_id,
               any(owner) as owner,
               any(repo) as repo,
               argMax(state, TS) as state,
               max(TS) AS ts
        FROM (
              SELECT task_id,
                     subtask_id,
                     any(task_repo)         AS repo,
                     any(task_owner)        AS owner,
                     argMax(task_state, ts) AS state,
                     argMax(is_deleted, ts) AS deleted,
                     max(ts)                AS TS
              FROM TasksSearch
              WHERE task_id IN (
                  SELECT DISTINCT task_id
                  FROM TasksSearch
                  WHERE {where}
                  {branch}
                  {owner}
              )
              GROUP BY task_id,
                       subtask_id
                 )
        WHERE (subtask_id = 0)
           OR (deleted = 0)
        GROUP BY task_id
    ) WHERE state != 'DELETED'
        {state}
)
SELECT
    task_id,
    repo,
    state,
    owner,
    try,
    iter,
    task_changed,
    message,
    stage,
    depends
FROM task_search
LEFT JOIN (
    SELECT
        task_id,
        argMax(try, changed) AS try,
        argMax(iter, changed) AS iter,
        argMax(message, changed) AS message,
        max(changed) AS task_changed,
        argMax(task_stage, changed) AS stage,
        argMax(depends, changed) AS depends
    FROM (
            SELECT * FROM (
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
                    GROUP BY task_id
                    ) AS TT ON TT.task_id = TaskProgress.task_id
                WHERE type = 'state'
                GROUP BY task_id, task_stage
            ) WHERE (state != 'DELETED')
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
                GROUP BY task_id
                ) AS TI ON TI.task_id = TaskStates.task_id
            GROUP BY task_id, try, iter
    )
    GROUP BY task_id
) AS TT ON TT.task_id = task_search.task_id
ORDER BY ts DESC
"""

    get_task_subtasks = """
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
        WHERE (task_id in (SELECT task_id FROM {tmp_table}))
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
        WHERE (task_id in (SELECT task_id FROM {tmp_table}))
        GROUP BY task_id, subtask_id
    ) WHERE sub_type != 'unknown'
)
GROUP BY task_id, subtask_id
ORDER BY subtask_id
"""

    get_task_table = """
SELECT argMax(table, change)
FROM (
      SELECT task_id,
             argMax(task_state, ts) AS state,
             max(ts) AS change,
             'progress' AS table
      FROM TaskProgress
      WHERE task_id = {id}
      GROUP BY task_id, table
      UNION ALL
      SELECT task_id,
             argMax(task_state, task_changed) AS state,
             max(task_changed) AS change,
             'state' AS table
      FROM TaskStates
      WHERE task_id = {id}
      GROUP BY task_id, table
)
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
SELECT task_id,
       argMax(task_repo, ts),
       TS.state,
       argMax(task_owner, ts),
       TS.try,
       TS.iter,
       TS.changed,
       TS.message,
       TS.task_stage,
       TS.depends,
       TS.task_iters
FROM TasksSearch
LEFT JOIN (
    SELECT
        task_id,
        argMax(task_state, task_changed) AS state,
        TI.try AS try,
        TI.iter AS iter,
        argMax(task_message, task_changed) AS message,
        max(task_changed) as changed,
        argMax(task_depends, task_changed) AS depends,
        '' as task_stage,
        iters as task_iters
    FROM TaskStates
    LEFT JOIN (
        SELECT
            task_id,
            argMax(task_try, task_changed) AS try,
            argMax(task_iter, task_changed) AS iter,
            TI.prev_iter AS iters
        FROM TaskIterations
        LEFT JOIN (
            SELECT task_id, groupUniqArray((task_try, task_iter)) AS prev_iter
            FROM TaskIterations
            WHERE task_try != 0
                AND task_id = {id}
            GROUP BY task_id
        ) AS TI ON TI.task_id = TaskIterations.task_id
        WHERE task_id = {id}
        GROUP BY task_id, iters
        ) AS TI ON TI.task_id = TaskStates.task_id
    WHERE task_id = {id}
    GROUP BY task_id, try, iter, task_iters
) AS TS ON TS.task_id = TasksSearch.task_id
WHERE task_id = {id}
GROUP BY
    task_id,
    TS.state,
    TS.try,
    TS.iter,
    TS.message,
    TS.changed,
    TS.depends,
    TS.task_stage,
    TS.task_iters
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
