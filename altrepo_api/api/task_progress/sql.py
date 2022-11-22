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

    get_tasks_by_id = """
SELECT task_id,
       argMax(owner, changed),
       argMax(task_repo, changed),
       argMax(state, changed),
       max(changed) AS task_changed
FROM (
    SELECT *
    FROM (
        SELECT task_id,
               argMax(task_owner, ts) AS owner,
               task_repo,
               argMax(task_state, ts) AS state,
               max(ts) AS changed
        FROM TaskProgress
        WHERE toString(task_id) ILIKE '%{task_id}%'
        {branch}
        GROUP BY task_id, task_repo
        )
    WHERE state != 'DELETED'
    UNION ALL
    SELECT *
    FROM (
        SELECT task_id,
               any(task_owner) AS owner,
               task_repo,
               any(TT.state),
               max(task_changed) AS changed
        FROM Tasks
        LEFT JOIN (
            SELECT task_id, argMax(task_state, ts) AS state
            FROM TaskStates
            WHERE toString(task_id) ILIKE '%{task_id}%'
            GROUP BY task_id
        ) AS TT ON TT.task_id = Tasks.task_id
        WHERE TT.state != 'DELETED'
            AND toString(task_id) ILIKE '%{task_id}%'
            {branch}
        GROUP BY task_id, task_repo
        )
)
GROUP BY task_id
ORDER BY task_changed DESC
{limit}
"""

    get_tasks_by_owner = """
SELECT task_id,
       argMax(owner, changed),
       argMax(task_repo, changed),
       argMax(state, changed),
       max(changed) AS task_changed
FROM (
    SELECT *
    FROM (
        SELECT
            task_id,
            argMax(task_owner, ts) AS owner,
            argMax(task_repo, ts) AS task_repo,
            argMax(task_state, ts) AS state,
            max(ts) AS changed
        FROM TaskProgress
        WHERE task_owner ILIKE '%{owner}%'
        GROUP BY task_id
        )
    WHERE state != 'DELETED'
    {branch}
    UNION ALL
    SELECT *
    FROM (
        SELECT
            task_id,
            any(TT.owner),
            TT.task_repo as task_repo,
            argMax(task_state, task_changed) AS state,
            max(task_changed) AS changed
        FROM TaskStates
        LEFT JOIN (
            SELECT
                task_id,
                task_repo,
                any(task_owner) AS owner
            FROM Tasks
            WHERE task_owner ILIKE '%{owner}%'
                {branch}
            GROUP BY task_id, task_repo
        ) AS TT ON TT.task_id = TaskStates.task_id
        WHERE TT.owner ILIKE '%{owner}%'
            {branch}
        GROUP BY task_id, task_repo
        ) WHERE state != 'DELETED'
)
GROUP BY task_id
ORDER BY task_changed DESC
{limit}
"""

    get_tasks_by_comp = """
WITH stp_components AS (
    SELECT task_id,
           argMax(subtask_srpm, ts) AS srpm,
           argMax(subtask_srpm_name, ts) AS srpm_name,
           argMax(subtask_dir, ts) AS dir,
           argMax(subtask_package, ts) AS package,
           argMax(type, ts) AS sub_type
    FROM TaskSubtaskProgress
    WHERE (type != 'progress')
    {branch}
    GROUP BY task_id,
             subtask_id
),
t_components AS (
    SELECT
        task_id,
        argMax(subtask_srpm, task_changed) AS srpm,
        argMax(subtask_srpm_name, task_changed) AS srpm_name,
        argMax(subtask_dir, task_changed) AS dir,
        argMax(subtask_package, task_changed) AS package,
        max(task_changed) AS changed
    FROM Tasks
    WHERE subtask_deleted = 0
    {branch}
    GROUP BY task_id
)
SELECT
    task_id,
    argMax(owner, changed),
    argMax(task_repo, changed),
    argMax(state, changed),
    max(changed) AS task_changed
FROM (
    SELECT *
    FROM (
        SELECT
            task_id,
            argMax(task_owner, ts) AS owner,
            task_repo,
            argMax(task_state, ts) AS state,
            max(ts) AS changed
        FROM TaskProgress
        WHERE task_id IN (
            SELECT task_id FROM stp_components
            WHERE (
                srpm ILIKE '%{comp}%'
                OR srpm_name ILIKE '%{comp}%'
                OR dir ILIKE '%{comp}%'
                OR package ILIKE '%{comp}%'
            )
        )
        {branch}
        GROUP BY task_id, task_repo
    )
    WHERE state != 'DELETED'
    UNION ALL
    SELECT
        task_id,
        any(task_owner) AS owner,
        task_repo,
        any(TT.state),
        max(task_changed) AS changed
    FROM Tasks
    LEFT JOIN (
        SELECT task_id, argMax(task_state, task_changed) AS state
        FROM TaskStates
        GROUP BY task_id
    ) AS TT ON TT.task_id = Tasks.task_id
    WHERE TT.state != 'DELETED'
    AND task_id IN (
        SELECT task_id
        FROM t_components
        WHERE (
            srpm ILIKE '%{comp}%'
            OR srpm_name ILIKE '%{comp}%'
            OR dir ILIKE '%{comp}%'
            OR package ILIKE '%{comp}%'
        )
    )
    {branch}
    GROUP BY task_id, task_repo
)
GROUP BY task_id
ORDER BY task_changed DESC
{limit}
"""

    get_task_components = """
WITH stp_components AS (
    SELECT task_id,
           argMax(subtask_srpm, ts) AS srpm,
           argMax(subtask_srpm_name, ts) AS srpm_name,
           argMax(subtask_srpm_evr, ts) AS srpm_evr,
           argMax(subtask_dir, ts) AS dir,
           argMax(subtask_tag_name, ts) AS tag_name,
           argMax(subtask_package, ts) AS package,
           argMax(type, ts) AS sub_type,
           max(ts) AS changed
    FROM TaskSubtaskProgress
    WHERE task_id IN (SELECT task_id FROM {tmp_table})
      AND (type != 'progress')
    GROUP BY task_id,
             subtask_id
    ORDER BY changed desc 
)
SELECT DISTINCT *
FROM (
    SELECT 
        task_id,
        srpm,
        srpm_name,
        srpm_evr,
        dir,
        tag_name,
        package
    FROM stp_components
    WHERE sub_type != 'delete'
    UNION ALL
    SELECT task_id,
        argMax(subtask_srpm, task_changed) AS srpm,
        argMax(subtask_srpm_name, task_changed) AS srpm_name,
        argMax(subtask_srpm_evr, task_changed) AS srpm_evr,
        argMax(subtask_dir, task_changed) AS dir,
        argMax(subtask_tag_name, task_changed) AS tag_name,
        argMax(subtask_package, task_changed) AS package
    FROM Tasks
    WHERE task_id IN (SELECT task_id FROM {tmp_table})
        AND subtask_deleted = 0
    GROUP BY task_id, task_changed
    ORDER BY task_changed desc 
)     
"""

    check_owner = """
SELECT task_owner
FROM Tasks
WHERE task_owner ILIKE '%{owner}%'    
"""


sql = SQL()
