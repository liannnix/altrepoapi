# ALTRepo API
# Copyright (C) 2021-2023  BaseALT Ltd

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
AND task_state = 'DONE'
"""

    get_task_list = """
WITH global_search AS (
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
            WHERE type = 'task'
            {where_clause_tasks}
            GROUP BY lead
            ORDER BY max(ts) DESC
        )
        WHERE search LIKE '%|DONE|%'
        AND task_id IN (
             SELECT task_id FROM (
                 SELECT
                    task_id,
                    subtask_id,
                    argMax(subtask_type, ts) AS sub_type,
                    argMax(subtask_srpm, ts) AS srpm,
                    argMax(subtask_dir, ts) AS dir,
                    argMax(subtask_package, ts) AS package,
                    if(has(groupUniqArray(subtask_deleted), 0), 'create', 'delete') AS tp
                FROM Tasks
                GROUP BY task_id, subtask_id
             ) WHERE (sub_type != 'unknown' OR arrayFilter(x -> notEmpty(x), [srpm, package, dir]) != []) AND (tp != 'delete') AND (sub_type != 'delete')
         )
        {where_clause_tasks2}
    )
),
errata_tasks AS (
    SELECT
        errata_id,
        argMax(task_id, ts) AS tsk_id,
        argMax(eh_references.link, ts) AS refs_links,
        argMax(eh_references.type, ts) AS refs_types,
        max(eh_updated) AS changed
    FROM ErrataHistory
    WHERE eh_type = 'task' AND errata_id IN (
    SELECT eid
    FROM (
        SELECT
            errata_id_noversion,
            argMax(errata_id, errata_id_version) AS eid
        FROM ErrataHistory
        WHERE task_state = 'DONE' AND pkgset_name != 'icarus'
        {branch_errata_clause}
        GROUP BY errata_id_noversion
    )
)
GROUP BY errata_id
)
SELECT global_search.*,
       TT.errata_id,
       TT.refs_links,
       TT.refs_types
FROM global_search
LEFT JOIN (
    SELECT  * FROM errata_tasks
) AS TT ON TT.tsk_id = global_search.task_id
{where_clause_errata}
"""

    get_subtasks = """
WITH pkg_hashes AS (
    SELECT task_id,
           subtask_id,
           titer_srcrpm_hash,
           subtask_arch
    FROM TaskIterations
    WHERE (task_id, task_changed) IN (SELECT task_id, changed FROM {tmp_table})
      AND titer_srcrpm_hash != 0
),
tasks_info AS (
    SELECT
        task_id,
        subtask_id,
        argMax(subtask_type, ts) AS sub_type,
        argMax(subtask_changed, ts) AS changed,
        if(has(groupUniqArray(subtask_deleted), 0), 'create', 'delete') AS tp
    FROM Tasks
    WHERE task_id IN (SELECT task_id FROM pkg_hashes)
    GROUP BY task_id, subtask_id
)
SELECT task_id,
       subtask_id,
       sub_type,
       changed,
       tp,
       toString(TT.titer_srcrpm_hash),
       TT.pkg_name,
       TT.pkg_version,
       TT.pkg_release
FROM tasks_info
LEFT JOIN (
    SELECT
    task_id,
    subtask_id,
    titer_srcrpm_hash,
    PKG.pkg_name AS pkg_name,
    PKG.pkg_version AS pkg_version,
    PKG.pkg_release AS pkg_release
    FROM pkg_hashes
    LEFT JOIN (
        SELECT pkg_name, pkg_hash, pkg_version, pkg_release
        FROM Packages
        WHERE pkg_hash IN (
            SELECT titer_srcrpm_hash FROM pkg_hashes
        )
    ) AS PKG ON PKG.pkg_hash = titer_srcrpm_hash
    GROUP BY 
        task_id,
        subtask_id,
        titer_srcrpm_hash,
        PKG.pkg_name,
        PKG.pkg_version,
        PKG.pkg_release
) AS TT ON TT.task_id = tasks_info.task_id AND TT.subtask_id = tasks_info.subtask_id
WHERE sub_type != 'delete' AND tp != 'delete' AND titer_srcrpm_hash != '0'
ORDER BY subtask_id
"""

    get_task_info = """
WITH
t_state AS (
    SELECT
        any(task_id) AS t_id,
        max(task_changed) AS changed,
        argMax(task_state, task_changed) AS state,
        argMax(task_message, task_changed) AS message
    FROM TaskStates
    WHERE task_id = {id}
    AND task_state = 'DONE'
)
SELECT
    t_id AS task_id,
    TI.repo,
    state,
    changed,
    message,
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
WHERE task_id IN (
    SELECT task_id FROM (
         SELECT
            task_id,
            subtask_id,
            argMax(subtask_type, ts) AS sub_type,
            argMax(subtask_srpm, ts) AS srpm,
            argMax(subtask_dir, ts) AS dir,
            argMax(subtask_package, ts) AS package,
            if(has(groupUniqArray(subtask_deleted), 0), 'create', 'delete') AS tp
        FROM Tasks
        WHERE task_id = {id}
        GROUP BY task_id, subtask_id
    ) WHERE (sub_type != 'unknown' OR arrayFilter(x -> notEmpty(x), [srpm, package, dir]) != []) AND (tp != 'delete') AND (sub_type != 'delete')
)
"""

    get_subtasks_by_task_id = """
WITH pkg_hashes AS (
    SELECT task_id,
           subtask_id,
           argMax(titer_srcrpm_hash, task_changed) as pkg_hash
    FROM TaskIterations
    WHERE task_id = {task_id}
      AND titer_srcrpm_hash != 0
    GROUP BY task_id, subtask_id
)
SELECT
    task_id,
    subtask_id,
    changed,
    pkg_hash,
    pkg_name,
    pkg_version,
    pkg_release,
    chlog_text,
    chlog_date,
    chlog_name,
    chlog_evr,
    EH.errata_id,
    EH.eh_created,
    EH.eh_update,
    EH.ref_links,
    EH.ref_types
FROM (
    SELECT *, TT.*
    FROM (
        SELECT
            task_id,
            subtask_id,
            argMax(subtask_type, ts) AS sub_type,
            argMax(subtask_srpm, ts) AS srpm,
            argMax(subtask_dir, ts) AS dir,
            argMax(subtask_package, ts) AS package,
            argMax(subtask_changed, ts) AS changed,
            if(has(groupUniqArray(subtask_deleted), 0), 'create', 'delete') AS tp
        FROM Tasks
        WHERE (task_id = {task_id})
        GROUP BY task_id, subtask_id
    ) AS ST
    LEFT JOIN (
        SELECT
        task_id,
        subtask_id,
        pkg_hash,
        PKG.pkg_name AS pkg_name,
        PKG.pkg_version AS pkg_version,
        PKG.pkg_release AS pkg_release,
        PKG.chlog_text AS chlog_text,
        PKG.chlog_date AS chlog_date,
        PKG.chlog_name AS chlog_name,
        PKG.chlog_evr AS chlog_evr
        FROM pkg_hashes
        LEFT JOIN (
            SELECT pkg_name,
                   pkg_hash,
                   pkg_version,
                   pkg_release,
                   chlog_text,
                   chlog_date,
                   chlog_name,
                   chlog_evr
            FROM BranchPackageHistory
            WHERE pkg_hash IN (
                SELECT pkg_hash FROM pkg_hashes
            )
            AND pkgset_name = '{branch}'
        ) AS PKG ON PKG.pkg_hash = pkg_hashes.pkg_hash
        GROUP BY
            task_id,
            subtask_id,
            pkg_hash,
            pkg_name,
            pkg_version,
            pkg_release,
            chlog_text,
            chlog_date,
            chlog_name,
            chlog_evr
    ) AS TT ON TT.task_id = ST.task_id AND TT.subtask_id = ST.subtask_id
    WHERE (tp != 'delete') AND (sub_type != 'delete') AND (sub_type != 'unknown'
        OR arrayFilter(x -> notEmpty(x), [srpm, package, dir]) != [])
    ORDER BY subtask_id
) AS SI
LEFT JOIN (
    SELECT
        task_id,
        subtask_id,
        argMax(errata_id, errata_id_version) AS errata_id,
        argMax(eh_references.link, ts) as ref_links,
        argMax(eh_references.type, ts) as ref_types,
        max(eh_updated) as eh_update,
        max(eh_created) as eh_created
    FROM ErrataHistory
    WHERE eh_type = 'task' AND task_id = {task_id}
    GROUP BY subtask_id, task_id
    ORDER BY subtask_id
) AS EH ON EH.task_id = SI.task_id AND EH.subtask_id = SI.subtask_id
"""


sql = SQL()
