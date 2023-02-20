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
"""

    check_task_in_branch = """
SELECT count(task_id)
FROM TaskStates
WHERE task_id = {id}
    AND task_id IN
    (
        SELECT task_id
        FROM Tasks
        WHERE task_repo = '{branch}'
    )
"""

    check_branch_has_tasks = """
SELECT count(task_id)
FROM Tasks
WHERE task_repo = '{branch}'
"""

    task_repo = """
SELECT any(task_repo)
FROM Tasks
WHERE task_id = {id}
"""

    task_state = """
SELECT argMax(task_state, task_changed)
FROM TaskStates
WHERE task_id = {id}
"""

    done_task_last_changed = """
SELECT max(task_changed)
FROM TaskStates
WHERE task_state = 'DONE' AND task_id = {id}
"""

    task_repo_owner = """
SELECT
    any(task_repo),
    any(task_owner)
FROM Tasks
WHERE task_id = {id}
"""

    task_all_iterations = """
SELECT DISTINCT
    task_try,
    task_iter,
    subtask_id,
    max(task_changed)
FROM TaskIterations
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
    FROM TaskIterations
    WHERE task_id = {id}
        AND (task_try, task_iter) = {ti}
) AS last_task_changed
SELECT *
FROM TaskIterations
WHERE task_id = {id}
    AND task_changed = last_task_changed
ORDER BY
    subtask_id,
    subtask_arch
"""

    task_iterations_by_task_changed = """
SELECT *
FROM TaskIterations
WHERE task_id = {id}
    AND task_changed = '{changed}'
ORDER BY
    subtask_id,
    subtask_arch
"""

    task_iterations_keys = [
        "task_id",
        "task_changed",
        "subtask_id",
        "subtask_arch",
        "titer_ts",
        "titer_status",
        "task_try",
        "task_iter",
        "titer_srcrpm_hash",
        "titer_pkgs_hash",
        "titer_chroot_base",
        "titer_chroot_br",
        "titer_buildlog_hash",
        "titer_srpmlog_hash",
    ]

    task_subtasks_by_ti = """
WITH
(
    SELECT max(task_changed) AS task_changed
    FROM TaskIterations
    WHERE task_id = {id}
        AND (task_try, task_iter) = {ti}
) AS last_task_changed
SELECT *
FROM Tasks
WHERE task_id = {id}
    AND task_changed = last_task_changed
    AND subtask_deleted = 0
ORDER BY subtask_id
"""

    task_subtasks_by_task_changed = """
SELECT *
FROM Tasks
WHERE task_id = {id}
    AND task_changed = '{changed}'
    AND subtask_deleted = 0
ORDER BY subtask_id
"""

    task_subtasks_keys = [
        "task_id",
        "subtask_id",
        "task_repo",
        "task_owner",
        "task_changed",
        "subtask_changed",
        "subtask_deleted",
        "subtask_userid",
        "subtask_dir",
        "subtask_package",
        "subtask_type",
        "subtask_pkg_from",
        "subtask_sid",
        "subtask_tag_author",
        "subtask_tag_id",
        "subtask_tag_name",
        "subtask_srpm",
        "subtask_srpm_name",
        "subtask_srpm_evr",
    ]

    task_state_by_ti = """
WITH
(
    SELECT max(task_changed) AS task_changed
    FROM TaskIterations
    WHERE task_id = {id}
        AND (task_try, task_iter) = {ti}
) AS last_task_changed
SELECT DISTINCT *
FROM TaskStates
WHERE task_id = {id}
    AND task_changed = last_task_changed
"""

    task_state_by_task_changed = """
SELECT DISTINCT *
FROM TaskStates
WHERE task_id = {id}
    AND task_changed = '{changed}'
"""

    task_state_keys = [
        "task_changed",
        "task_id",
        "task_state",
        "task_runby",
        "task_depends",
        "task_try",
        "task_testonly",
        "task_failearly",
        "task_shared",
        "task_message",
        "task_version",
        "task_prev",
        "task_eventlog_hash",
    ]

    task_state_last = """
SELECT
    argMax(task_state, task_changed),
    argMax(task_message, task_changed),
    max(task_changed)
FROM TaskStates
WHERE task_id = {id}
"""

    task_plan_packages = """
SELECT
    pkg_hash,
    pkg_name,
    pkg_version,
    pkg_release,
    pkg_filename,
    pkg_arch,
    pkg_sourcepackage
FROM Packages
WHERE pkg_hash IN
(
    SELECT pkgh_mmh
    FROM PackageHash
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
SELECT DISTINCT
    subtask_arch,
    task_try,
    task_iter
FROM TaskIterations
WHERE task_id = {id}
    AND (task_try, task_iter) IN
    (
        SELECT
            argMax(task_try, task_changed),
            argMax(task_iter, task_changed)
        FROM TaskIterations
        WHERE task_id = {id}
    )
GROUP BY
    subtask_id,
    subtask_arch,
    task_try,
    task_iter
ORDER BY subtask_id
"""

    repo_single_task_plan_hshs = """
SELECT pkgh_mmh
FROM PackageHash
WHERE pkgh_sha256 IN
(
    SELECT tplan_sha256
    FROM TaskPlanPkgHash
    WHERE  tplan_hash IN %(hshs)s
        AND tplan_action = %(act)s
)
"""

    repo_tasks_diff_list_before_task = """
WITH
(
    SELECT max(task_changed)
    FROM TaskStates
    WHERE (task_state = 'DONE') AND (task_id =
    (
        SELECT argMax(task_prev, task_changed)
        FROM TaskStates
        WHERE (task_id = {id}) AND task_prev != 0
    ))
) AS current_task_prev_changed,
(
    SELECT max(task_changed)
    FROM TaskStates
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
            FROM TaskStates
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

    repo_last_repo_hashes_before_task = """
WITH
(
    SELECT max(task_changed)
    FROM TaskStates
    WHERE (task_id = {id}) AND (task_prev != 0)
) AS current_task_last_changed
SELECT pkg_hash
FROM PackageSet
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
                FROM TaskStates
            ) AS T ON T.task_id = toUInt32(pkgset_kv.v[indexOf(pkgset_kv.k, 'task')])
            WHERE pkgset_nodename = '{repo}'
            ORDER BY changed DESC
        )
        WHERE changed < current_task_last_changed
        LIMIT 1
    )
)
"""

    repo_last_repo_hashes = """
SELECT pkg_hash
FROM static_last_packages
WHERE pkgset_name = '{repo}'
"""

    repo_last_repo_tasks_diff_list = """
WITH
(
    SELECT max(pkgset_date)
    FROM static_last_packages
    WHERE pkgset_name = '{repo}'
) AS last_repo_date,
(
    SELECT toUInt32(pkgset_kv.v[indexOf(pkgset_kv.k, 'task')])
    FROM PackageSetName
    WHERE pkgset_nodename = '{repo}' AND pkgset_date = last_repo_date
) AS last_repo_task,
(
    SELECT max(task_changed)
    FROM TaskStates
    WHERE (task_state = 'DONE') AND task_id = last_repo_task
) AS last_repo_task_changed
SELECT task_id
FROM TaskStates
WHERE task_state = 'DONE'
    AND task_changed > last_repo_task_changed
    AND task_id IN (SELECT task_id FROM Tasks WHERE task_repo = '{repo}')
ORDER BY task_changed DESC
"""

    repo_last_repo_content = """
WITH
(
    SELECT max(task_changed)
    FROM TaskStates
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
            FROM TaskStates
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
FROM PackageHash
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
FROM Packages
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
FROM Packages
WHERE pkg_hash IN
(
    SELECT * FROM {table}
)
    AND pkg_name NOT LIKE '%%-debuginfo'
ORDER BY pkg_name
"""

    diff_repo_pkgs = """
SELECT pkg_hash
FROM Packages
WHERE pkg_hash IN
(
    SELECT * FROM {tmp_table1}
)
    AND
    (
        pkg_name IN
        (
            SELECT DISTINCT pkg_name
            FROM Packages
            WHERE pkg_hash IN
            (
                SELECT * FROM {tmp_table2}
            )
                AND pkg_name NOT LIKE '%%-debuginfo'
        )
        OR pkg_name IN
        (
            SELECT DISTINCT pkg_name
            FROM Packages
            WHERE pkg_hash IN
            (
                SELECT * FROM {tmp_table3}
            )
                AND pkg_name NOT LIKE '%%-debuginfo'
        )
    )
"""

    diff_depends_by_hshs = """
SELECT
    pkg_name,
    dp_type,
    if(pkg_sourcepackage = 0, pkg_arch, 'src') AS arch,
    groupUniqArray(tuple(dp_name, bitAnd(0xe, dp_flag), dp_version))
FROM Packages
INNER JOIN
(
    SELECT DISTINCT
        pkg_hash,
        dp_name,
        dp_flag,
        dp_version,
        dp_type
    FROM Depends
    WHERE pkg_hash IN
    (
        SELECT * FROM {table}
    )
) AS Deps USING pkg_hash
WHERE pkg_name NOT LIKE '%%-debuginfo'
GROUP BY
    pkg_name,
    arch,
    dp_type
"""

    build_task_src_packages = """
WITH
(
    SELECT max(task_changed)
    FROM TaskIterations
    WHERE task_id = {id}
) as last_changed
SELECT DISTINCT pkg_name
FROM Packages
WHERE pkg_hash IN
(
    SELECT titer_srcrpm_hash
    FROM TaskIterations
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

    misconflict_get_pkgs_of_task = """
WITH
    (
        SELECT max(task_changed)
        FROM TaskIterations
        WHERE task_id = {id}
    ) AS last_changed
SELECT DISTINCT
    pkg_name,
    pkg_hash
FROM Packages
WHERE pkg_hash IN
(
    SELECT arrayJoin(titer_pkgs_hash)
    FROM TaskIterations
    WHERE task_id = {id}
        AND task_changed = last_changed
)
"""

    get_branch_with_pkgs = """
SELECT DISTINCT
    pkgset_name,
    sourcepkgname,
    toString(any(pkgset_date)) AS pkgset_date,
    groupUniqArray(pkg_name) AS pkgnames,
    pkg_version,
    pkg_release,
    any(pkg_disttag),
    any(pkg_packager_email),
    toString(toDateTime(any(pkg_buildtime))) AS buildtime,
    groupUniqArray(pkg_arch)
FROM last_packages_with_source
WHERE sourcepkgname IN %(pkgs)s
    AND pkg_name NOT LIKE '%%-debuginfo'
    {branchs}
GROUP BY
    pkgset_name,
    sourcepkgname,
    pkg_version,
    pkg_release
ORDER BY pkgset_date DESC
"""

    task_src_packages = """
WITH
(
    SELECT max(task_changed)
    FROM TaskIterations
    WHERE task_id = {id}
) as last_changed
SELECT DISTINCT pkg_name
FROM Packages
WHERE pkg_hash IN
(
    SELECT titer_srcrpm_hash
    FROM TaskIterations
    WHERE task_id = {id}
        AND task_changed = last_changed
)
"""

    task_src_pkg_hashes = """
WITH
(
    SELECT max(task_changed)
    FROM TaskIterations
    WHERE task_id = {id}
) as last_changed
SELECT DISTINCT pkg_hash
FROM
(
    SELECT titer_srcrpm_hash AS pkg_hash
    FROM TaskIterations
    WHERE task_id = {id}
        AND task_changed = last_changed
)
"""

    get_task_history = """
WITH
pkgset_history AS
(
    SELECT
        pkgset_date,
        toUInt32(pkgset_kv.v[indexOf(pkgset_kv.k, 'task')]) AS pkgset_task
    FROM PackageSetName
    WHERE pkgset_nodename = '{branch}'
        AND pkgset_depth = 0
        AND pkgset_date >= '{t1_changed}'
        AND pkgset_date <= '{t2_changed}'
)
SELECT DISTINCT
    task_id,
    max(task_changed) AS changed,
    any(B.pkgset_date),
    any(B.pkgset_task)
FROM TaskStates
LEFT JOIN
(
    SELECT pkgset_date, pkgset_task
    FROM pkgset_history
) AS B ON B.pkgset_task = TaskStates.task_id
WHERE task_id IN
(
    SELECT task_id FROM Tasks WHERE task_repo = '{branch}'
)
    AND task_state = 'DONE'
    AND task_changed >= '{t1_changed}'
    AND task_changed <= '{t2_changed}'
GROUP BY task_id
ORDER BY changed DESC
"""

    get_last_task_info = """
WITH
    last_task_state AS
    (
        SELECT
            task_id,
            argMax(task_state, task_changed) AS state,
            argMax(task_message, task_changed) AS message,
            max(task_changed) AS changed
        FROM TaskStates
        WHERE task_id = {task_id}
        GROUP BY task_id
    ),
    task_try_iter AS
    (
        SELECT DISTINCT
            task_id,
            task_try,
            task_iter
        FROM TaskIterations
        WHERE (task_id, task_changed) = (
            SELECT
                task_id,
                changed
            FROM last_task_state
        )
    ),
    (
        SELECT DISTINCT task_repo
        FROM Tasks
        WHERE task_id = {task_id}
    ) AS task_branch
SELECT
    *,
    task_branch
FROM last_task_state
LEFT JOIN task_try_iter AS TI USING (task_id)
"""

    get_subtasks_binaries_with_sources = """
WITH all_sources AS
(
    -- added source packages
    SELECT
        task_id,
        subtask_id,
        'build' AS action,
        srcpkg_hash
    FROM Tasks
    INNER JOIN (
        SELECT DISTINCT
            task_id,
            subtask_id,
            titer_srcrpm_hash AS srcpkg_hash
        FROM TaskIterations
        WHERE (task_id, task_changed) = ({task_id}, '{task_changed}')
            AND (titer_status != 'deleted')
    ) AS T USING (task_id, subtask_id)
    WHERE (subtask_type != 'delete')
        AND (subtask_deleted = 0)
        AND (task_id, task_changed) = ({task_id}, '{task_changed}')
    UNION ALL
    -- deleted source packages
    SELECT
        task_id,
        subtask_id,
        'delete' AS action,
        pkg_hash AS srcpkg_hash
    FROM Packages
    INNER JOIN (
        SELECT
            task_id,
            subtask_id,
            subtask_package
        FROM Tasks
        WHERE (subtask_deleted = 0)
            AND (subtask_type = 'delete')
            AND (task_id, task_changed) = ({task_id}, '{task_changed}')
    ) AS T ON T.subtask_package = pkg_name
    WHERE pkg_hash IN (
        SELECT pkgh_mmh
        FROM PackageHash
        WHERE pkgh_sha256 IN (
            SELECT tplan_sha256
            FROM TaskPlanPkgHash
            WHERE (tplan_hash IN murmurHash3_64('{task_id}{task_try}{task_iter}src'))
                AND (tplan_action = 'delete')
        )
    )
)
SELECT DISTINCT
    subtask_id,
    action,
    sourcepkgname AS srcpkg_name,
    pkg_version,
    pkg_release,
    pkg_name AS binpkg_name,
    pkg_arch AS binpkg_arch
FROM all_packages_with_source
INNER JOIN all_sources AS S
    ON pkg_srcrpm_hash = S.srcpkg_hash
WHERE pkg_sourcepackage = 0
    AND pkg_srcrpm_hash IN (SELECT srcpkg_hash FROM all_sources)
    AND (pkg_arch IN {archs})
"""

    get_task_arepo_packages = """
WITH task_plan_hashes AS
    (
        SELECT pkgh_mmh
        FROM PackageHash
        WHERE pkgh_sha256 IN (
            SELECT tplan_sha256
            FROM TaskPlanPkgHash
            WHERE (tplan_hash IN murmurHash3_64('{task_id}{task_try}{task_iter}x86_64-i586'))
                AND (tplan_action = 'add')
        )
    )
SELECT
    pkg_name,
    pkg_version,
    pkg_release
FROM Packages
WHERE pkg_hash IN (task_plan_hashes)
"""

    get_images_by_binary_pkgs_names = """
SELECT DISTINCT
    img_file,
    img_edition,
    img_tag,
    pkgset_date AS img_buildtime,
    pkg_name,
    pkg_version,
    pkg_release,
    pkg_arch,
    pkg_hash
FROM lv_all_image_packages
WHERE (pkg_hash IN (
    SELECT DISTINCT pkg_hash
    FROM Packages
    WHERE (pkg_name IN (SELECT pkg_name FROM {tmp_table}))
    AND (pkg_sourcepackage = 0)
))
AND (img_branch = '{branch}')
AND (img_tag IN (
    SELECT img_tag
    FROM (
        SELECT img_tag, argMax(img_show, ts) AS img_show
        FROM ImageTagStatus
        GROUP BY img_tag
    )
    WHERE img_show = 'show'
))
"""


sql = SQL()
