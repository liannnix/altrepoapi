from dataclasses import dataclass

@dataclass(frozen=True)
class SQL:
    check_task = """
SELECT count(task_id)
FROM TaskStates_buffer
WHERE task_id = {id}
"""

    get_task_repo = """
SELECT any(task_repo)
FROM Tasks_buffer
WHERE task_id = {id}
"""

    get_task_info = """
SELECT DISTINCT TI.try_iter, task_repo, task_owner
FROM Tasks_buffer
LEFT JOIN
(
    SELECT task_id, concat(toString(task_try), '.', toString(task_iter)) AS try_iter
    FROM TaskIterations_buffer
) AS TI USING task_id
WHERE task_id = {id}
"""

    get_task_content = """
SELECT titer_srcrpm_hash,
    TS.task_state AS status,
    subtask_id,
    concat(toString(task_try), '.', toString(task_iter)) AS ti,
    groupUniqArray(arrayJoin(titer_pkgs_hash)),
    any(TS.task_message) as message
FROM TaskIterations_buffer
CROSS JOIN 
(
    SELECT argMax(task_state, task_changed) AS task_state,
        argMax(task_message, task_changed) AS task_message
    FROM TaskStates_buffer
    WHERE task_id = {id}
) AS TS
WHERE task_id = {id}
    AND (task_try, task_iter) IN
    (
        SELECT argMax(task_try, task_changed),
            argMax(task_iter, task_changed)
        FROM TaskIterations_buffer
        WHERE task_id = {id}
    )
GROUP BY titer_srcrpm_hash,
        status,
        subtask_id,
        ti
ORDER BY subtask_id
"""

    get_task_content_rebuild = """
SELECT titer_srcrpm_hash,
    TS.task_state AS status,
    subtask_id,
    concat(toString(task_try), '.', toString(task_iter)) AS ti,
    groupUniqArray(arrayJoin(titer_pkgs_hash)),
    any(TS.task_message) as message
FROM TaskIterations_buffer
CROSS JOIN
(
    SELECT argMax(task_state, task_changed) AS task_state,
        argMax(task_message, task_changed) AS task_message
    FROM TaskStates_buffer
    WHERE task_id = {id}
) AS TS
WHERE task_id = {id}
    AND (task_try, task_iter) = {ti}
GROUP BY titer_srcrpm_hash,
        status,
        subtask_id,
        ti
ORDER BY subtask_id
"""

    get_packages_info = """
SELECT pkg_hash,
    pkg_name,
    pkg_version,
    pkg_release,
    pkg_arch,
    pkg_description
FROM Packages_buffer
WHERE pkg_hash IN {hshs}
"""

    get_task_approvals = """
SELECT res
FROM
(
    SELECT argMax(tuple(subtask_id, toString(tapp_date), tapp_type,
        tapp_name, tapp_message, tapp_revoked), ts) AS res
    FROM TaskApprovals
    WHERE task_id = {id}
    GROUP BY (subtask_id, tapp_name)
)
WHERE tupleElement(res, 6) = 0
"""

    repo_get_task_content = """
SELECT titer_srcrpm_hash,
    subtask_id,
    subtask_arch,
    task_try,
    task_iter,
    groupUniqArray(arrayJoin(titer_pkgs_hash))
FROM TaskIterations_buffer
WHERE task_id = {id}
    AND (task_try, task_iter) IN
    (
        SELECT argMax(task_try, task_changed), argMax(task_iter, task_changed)
        FROM TaskIterations_buffer
        WHERE task_id = {id}
    )
GROUP BY titer_srcrpm_hash,
        subtask_id,
        subtask_arch,
        task_try,
        task_iter
ORDER BY subtask_id
"""

    repo_get_single_task_plan_hshs = """
SELECT pkgh_mmh
FROM PackageHash_buffer
WHERE pkgh_sha256 IN
(
    SELECT tplan_sha256
    FROM TaskPlanPkgHash
    WHERE  tplan_hash IN %(hshs)s
        AND tplan_action = %(act)s
)
"""

    repo_get_tasks_diff_list = """
WITH
    (
        SELECT max(task_changed)
        FROM TaskStates_buffer
        WHERE (task_state = 'DONE') AND (task_id = 
        (
            SELECT argMax(task_prev, task_changed)
            FROM TaskStates
            WHERE (task_id = {id}) AND task_prev != 0
        ))
    ) AS current_task_prev_changed,
    (
        SELECT max(task_changed)
        FROM TaskStates_buffer
        WHERE (task_id = {id}) AND (task_prev != 0)
    ) AS current_task_last_changed,
    (
        SELECT changed
        FROM 
        (
            SELECT T.task_changed AS changed
            FROM PackageSetName
            INNER JOIN
            (
                SELECT task_id, task_changed
                FROM TaskStates_buffer
            ) AS T ON T.task_id = toUInt32(pkgset_kv.v[indexOf(pkgset_kv.k, 'task')])
            WHERE pkgset_nodename = '{repo}'
            ORDER BY changed DESC
        )
        WHERE changed < current_task_last_changed
        LIMIT 1
    ) AS last_repo_task_changed
SELECT task_id
FROM TaskStates
WHERE task_state = 'DONE'
    AND task_changed <= current_task_prev_changed
    AND task_changed > last_repo_task_changed
    AND task_id IN (SELECT task_id FROM Tasks WHERE task_repo = '{repo}')
ORDER BY task_changed DESC
"""

    repo_get_last_repo = """
WITH
    (
        SELECT max(task_changed)
        FROM TaskStates_buffer
        WHERE (task_id = {id}) AND (task_prev != 0)
    ) AS current_task_last_changed
SELECT pkg_hash
FROM PackageSet_buffer
WHERE pkgset_uuid IN
(
    SELECT pkgset_uuid FROM PackageSetName
    WHERE pkgset_ruuid IN
    (
        SELECT pkgset_uuid
        FROM
        (
            SELECT pkgset_uuid, T.task_changed AS changed
            FROM PackageSetName
            INNER JOIN
            (
                SELECT task_id, task_changed
                FROM TaskStates_buffer
            ) AS T ON T.task_id = toUInt32(pkgset_kv.v[indexOf(pkgset_kv.k, 'task')])
            WHERE pkgset_nodename = '{repo}'
            ORDER BY changed DESC
        )
        WHERE changed < current_task_last_changed
        LIMIT 1
    )
)
"""

    repo_get_last_repo_content = """
WITH
    (
        SELECT max(task_changed)
        FROM TaskStates_buffer
        WHERE (task_id = {id}) AND (task_prev != 0)
    ) AS current_task_last_changed
SELECT pkgset_nodename,
    pkgset_date,
    pkgset_tag,
    pkgset_kv.k,
    pkgset_kv.v
FROM PackageSetName
WHERE pkgset_uuid IN
(
    SELECT pkgset_uuid
    FROM
    (
        SELECT pkgset_uuid, T.task_changed AS changed
        FROM PackageSetName
        INNER JOIN
        (
            SELECT task_id, task_changed
            FROM TaskStates_buffer
        ) AS T ON T.task_id = toUInt32(pkgset_kv.v[indexOf(pkgset_kv.k, 'task')])
        WHERE pkgset_nodename = '{repo}'
        ORDER BY changed DESC
    )
    WHERE changed < current_task_last_changed
    LIMIT 1
)
"""

    repo_get_tasks_plan_hshs = """
SELECT DISTINCT pkgh_mmh
FROM PackageHash_buffer
WHERE pkgh_sha256 IN (
    SELECT tplan_sha256
    FROM TaskPlanPkgHash
    WHERE tplan_hash IN (
        SELECT tplan_hash
        FROM task_plan_hashes
        WHERE task_id IN %(id)s
    )
    AND tplan_action = %(act)s
)
"""

    repo_create_tmp_table = """
CREATE TEMPORARY TABLE tmpPkgHashes (pkghash UInt64)
"""

    repo_insert_into_tmp_table = """
INSERT INTO tmpPkgHashes VALUES
"""

    repo_get_packages_by_hshs = """
SELECT DISTINCT 
    pkg_name,
    pkg_version,
    pkg_release,
    pkg_arch,
    pkg_filename,
    pkg_sourcepackage
FROM Packages_buffer
WHERE pkg_hash IN
(
    SELECT * FROM tmpPkgHashes
)
"""