from dataclasses import dataclass

@dataclass(frozen=True)
class SQL:
    check_task = """
SELECT count(task_id)
FROM TaskStates_buffer
WHERE task_id = {id}
"""

    task_repo = """
SELECT any(task_repo)
FROM Tasks_buffer
WHERE task_id = {id}
"""

    task_repo_owner = """
SELECT
    any(task_repo),
    any(task_owner)
FROM Tasks_buffer
WHERE task_id = {id}
"""

    task_all_iterations = """
SELECT DISTINCT
    task_try,
    task_iter,
    subtask_id,
    max(task_changed)
FROM TaskIterations_buffer
WHERE task_id = {id}
GROUP BY
    task_try,
    task_iter,
    subtask_id
ORDER BY
    task_try,
    task_iter,
    subtask_id
"""

    task_iterations_by_ti = """
WITH
(
    SELECT max(task_changed) AS task_changed
    FROM TaskIterations_buffer
    WHERE task_id = {id}
        AND (task_try, task_iter) = {ti}
) AS last_task_changed
SELECT *
FROM TaskIterations_buffer
WHERE task_id = {id}
    AND task_changed = last_task_changed
ORDER BY
    subtask_id,
    subtask_arch
"""

    task_iterations_by_task_changed = """
SELECT *
FROM TaskIterations_buffer
WHERE task_id = {id}
    AND task_changed = '{changed}'
ORDER BY
    subtask_id,
    subtask_arch
"""

    task_iterations_keys = [
        'task_id',
        'task_changed',
        'subtask_id',
        'subtask_arch',
        'titer_ts',
        'titer_status',
        'task_try',
        'task_iter',
        'titer_srcrpm_hash',
        'titer_pkgs_hash',
        'titer_chroot_base',
        'titer_chroot_br',
        'titer_buildlog_hash',
        'titer_srpmlog_hash'
    ]

    task_subtasks_by_ti = """
WITH
(
    SELECT max(task_changed) AS task_changed
    FROM TaskIterations_buffer
    WHERE task_id = {id}
        AND (task_try, task_iter) = {ti}
) AS last_task_changed
SELECT *
FROM Tasks_buffer
WHERE task_id = {id}
    AND task_changed = last_task_changed
    AND subtask_deleted = 0
ORDER BY subtask_id
"""

    task_subtasks_by_task_changed = """
SELECT *
FROM Tasks_buffer
WHERE task_id = {id}
    AND task_changed = '{changed}'
    AND subtask_deleted = 0
ORDER BY subtask_id
"""

    task_subtasks_keys = [
        'task_id',
        'subtask_id',
        'task_repo',
        'task_owner',
        'task_changed',
        'subtask_changed',
        'subtask_deleted',
        'subtask_userid',
        'subtask_dir',
        'subtask_package',
        'subtask_type',
        'subtask_pkg_from',
        'subtask_sid',
        'subtask_tag_author',
        'subtask_tag_id',
        'subtask_tag_name',
        'subtask_srpm',
        'subtask_srpm_name',
        'subtask_srpm_evr'
    ]

    task_state_by_ti = """
WITH
(
    SELECT max(task_changed) AS task_changed
    FROM TaskIterations_buffer
    WHERE task_id = {id}
        AND (task_try, task_iter) = {ti}
) AS last_task_changed
SELECT DISTINCT *
FROM TaskStates_buffer
WHERE task_id = {id}
    AND task_changed = last_task_changed
"""

    task_state_by_task_changed = """
SELECT DISTINCT *
FROM TaskStates_buffer
WHERE task_id = {id}
    AND task_changed = '{changed}'
"""

    task_state_keys = [
        'task_changed',
        'task_id',
        'task_state',
        'task_runby',
        'task_depends',
        'task_try',
        'task_testonly',
        'task_failearly',
        'task_shared',
        'task_message',
        'task_version',
        'task_prev',
        'task_eventlog_hash'
    ]

    task_plan_packages = """
SELECT
    pkg_hash,
    pkg_name,
    pkg_version,
    pkg_release,
    pkg_filename,
    pkg_arch,
    pkg_sourcepackage
FROM Packages_buffer
WHERE pkg_hash IN 
(
    SELECT pkgh_mmh
    FROM PackageHash_buffer
    WHERE pkgh_sha256 IN 
    (
        SELECT tplan_sha256
        FROM TaskPlanPkgHash
        WHERE tplan_hash IN {hshs}
            AND tplan_action = '{action}'
    )
)
"""

    task_approvals = """
SELECT res
FROM
(
    SELECT argMax(tuple(subtask_id, tapp_date, tapp_type,
        tapp_name, tapp_message, tapp_revoked), ts) AS res
    FROM TaskApprovals
    WHERE task_id = {id}
    GROUP BY (subtask_id, tapp_name)
)
WHERE tupleElement(res, 6) = 0
"""

    repo_task_content = """
SELECT
    subtask_arch,
    task_try,
    task_iter
FROM TaskIterations_buffer
WHERE task_id = {id}
    AND (task_try, task_iter) IN
    (
        SELECT
            argMax(task_try, task_changed),
            argMax(task_iter, task_changed)
        FROM TaskIterations_buffer
        WHERE task_id = {id}
    )
GROUP BY
    titer_srcrpm_hash,
    subtask_id,
    subtask_arch,
    task_try,
    task_iter
ORDER BY subtask_id
"""

    repo_single_task_plan_hshs = """
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

    repo_tasks_diff_list = """
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

    repo_last_repo = """
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

    repo_last_repo_content = """
WITH
    (
        SELECT max(task_changed)
        FROM TaskStates_buffer
        WHERE (task_id = {id}) AND (task_prev != 0)
    ) AS current_task_last_changed
SELECT
    pkgset_nodename,
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

    repo_tasks_plan_hshs = """
SELECT DISTINCT pkgh_mmh
FROM PackageHash_buffer
WHERE pkgh_sha256 IN
(
    SELECT tplan_sha256
    FROM TaskPlanPkgHash
    WHERE tplan_hash IN
    (
        SELECT tplan_hash
        FROM task_plan_hashes
        WHERE task_id IN %(id)s
    )
    AND tplan_action = %(act)s
)
"""

    create_tmp_hshs_table = """
CREATE TEMPORARY TABLE {table} (pkghash UInt64)
"""

    insert_into_tmp_hshs_table = """
INSERT INTO {table} VALUES
"""

    truncate_tmp_table = """
TRUNCATE TABLE {table}
"""

    repo_packages_by_hshs = """
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
    SELECT * FROM {table}
)
"""

    diff_packages_by_hshs = """
SELECT 
    pkg_name,
    pkg_arch,
    pkg_filename
FROM Packages_buffer
WHERE pkg_hash IN
(
    SELECT * FROM {table}
)
    AND pkg_name NOT LIKE '%%-debuginfo'
ORDER BY pkg_name
"""

    diff_repo_pkgs = """
SELECT pkg_hash
FROM Packages_buffer
WHERE pkg_hash IN
(
    SELECT * FROM {tmp_table1}
)
    AND pkg_name IN
    (
        SELECT DISTINCT pkg_name
        FROM Packages_buffer
        WHERE pkg_hash IN
        (
            SELECT * FROM {tmp_table2}
        )
            AND pkg_name NOT LIKE '%%-debuginfo'
    )
"""

    diff_depends_by_hshs = """
SELECT
    pkg_name,
    dp_type,
    pkg_arch,
    groupUniqArray(dp_name)
FROM Packages_buffer
INNER JOIN
(
    SELECT DISTINCT
        pkg_hash,
        dp_name,
        dp_type
    FROM Depends_buffer
    WHERE pkg_hash IN
    (
        SELECT * FROM {table}
    )
        AND dp_type IN
        (
            'provide',
            'require',
            'obsolete',
            'conflict'
        )
) AS Deps USING pkg_hash
WHERE pkg_name NOT LIKE '%%-debuginfo'
GROUP BY
    pkg_name,
    pkg_arch,
    dp_type
"""

    build_task_src_packages = """
WITH
(
    SELECT max(task_changed)
    FROM TaskIterations_buffer
    WHERE task_id = {id}
) as last_changed
SELECT DISTINCT pkg_name
FROM Packages_buffer
WHERE pkg_hash IN
(
    SELECT titer_srcrpm_hash
    FROM TaskIterations_buffer
    WHERE task_id = {id}
        AND task_changed = last_changed
)
UNION ALL
SELECT DISTINCT subtask_package
FROM Tasks
WHERE task_id = {id}
    AND task_changed = last_changed
    AND subtask_type = 'delete'
    AND subtask_deleted = 0
"""


tasksql = SQL()
