# ALTRepo API
# Copyright (C) 2021-2025  BaseALT Ltd

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
    create_tmp_table = """
CREATE TEMPORARY TABLE {tmp_table} {columns}
"""

    select_all_tmp_table = """
SELECT * FROM {tmp_table}
"""

    insert_into_tmp_table = """
INSERT INTO {tmp_table} (*) VALUES
"""

    get_tasks_by_pkg_name = """
WITH
last_task_states AS
(
    SELECT
        task_id,
        argMax(task_state, task_changed) AS task_state,
        max(task_changed) AS changed
    FROM TaskStates
    GROUP BY task_id
)
SELECT
    T1.*,
    groupUniqArray(tuple(T2.*)) AS gears
FROM
(
    SELECT DISTINCT
        task_id,
        TS.task_state,
        task_changed
    FROM TaskIterations
    INNER JOIN
    (
        SELECT task_id, task_state FROM last_task_states
    ) AS TS USING (task_id)
    WHERE titer_srcrpm_hash IN (
        SELECT pkg_hash
        FROM Packages
        WHERE (pkg_name LIKE '{name}') AND (pkg_sourcepackage = 1)
    ) AND (task_id, task_changed) IN
    (
        SELECT
            task_id,
            changed
        FROM last_task_states
    )
    UNION ALL
    SELECT DISTINCT
        task_id,
        TS.task_state,
        task_changed
    FROM Tasks
    INNER JOIN
    (
        SELECT task_id, task_state FROM last_task_states
    ) AS TS USING (task_id)
    WHERE subtask_deleted = 0
        AND subtask_package = '{name}'
        AND subtask_type = 'delete'
        AND (task_id, task_changed) IN
        (
            SELECT
                task_id,
                changed
            FROM last_task_states
        )
) AS T1
LEFT JOIN
(
    SELECT
        task_id,
        subtask_id,
        task_repo,
        task_owner,
        subtask_type,
        subtask_dir,
        subtask_tag_id,
        subtask_srpm_name,
        subtask_srpm_evr,
        subtask_package,
        subtask_pkg_from,
        task_changed
    FROM Tasks
    WHERE subtask_deleted = 0
) AS T2 USING (task_id, task_changed)
GROUP BY
    task_id,
    task_state,
    task_changed
ORDER BY task_changed DESC
"""

    get_pkg_names_by_task_ids = """
SELECT DISTINCT
    task_id,
    subtask_id,
    pkg_name,
    pkg_version,
    pkg_release
FROM TaskIterations
LEFT JOIN
(
    SELECT
        pkg_hash,
        pkg_name,
        pkg_version,
        pkg_release
    FROM Packages
    WHERE pkg_sourcepackage = 1
) AS P ON (pkg_hash = titer_srcrpm_hash)
WHERE (task_id, subtask_id) IN
(
    SELECT * FROM {tmp_table}
)
"""

    get_last_subtasks_branch_preselect = """
(
    SELECT DISTINCT
        task_id,
        task_changed,
        task_message
    FROM BranchPackageHistory
    WHERE pkgset_name = '{branch}'
    ORDER BY task_changed DESC
    LIMIT {limit}
)
"""

    get_last_subtasks_maintainer_preselect = """
(
    SELECT DISTINCT
        task_id ,
        task_changed,
        task_message
    FROM TaskStates
    WHERE task_state = 'DONE' AND task_id IN
    (
        SELECT DISTINCT task_id
        FROM Tasks
        WHERE task_repo = '{branch}'
            AND task_owner = '{task_owner}'
            AND task_id IN (
                SELECT task_id
                FROM TaskStates
                WHERE task_state = 'DONE'
            )
        ORDER BY task_changed DESC
        LIMIT {limit}
    )
)
"""

    get_last_subtasks_from_tasks = """
WITH
last_tasks AS
{last_tasks_preselect}
SELECT
    task_id,
    subtask_id,
    RQ.task_owner,
    task_changed,
    RQ.subtask_userid,
    RQ.subtask_type,
    RQ.subtask_package,
    RQ.subtask_srpm_name,
    RQ.subtask_pkg_from,
    titer_srcrpm_hash,
    LST.task_message
FROM
(
    SELECT DISTINCT
        task_id,
        subtask_id,
        TSK.task_owner,
        task_changed,
        TSK.subtask_userid,
        TSK.subtask_type,
        TSK.subtask_package,
        TSK.subtask_srpm_name,
        TSK.subtask_pkg_from,
        titer_srcrpm_hash
    FROM TaskIterations
    LEFT JOIN
    (
        SELECT
            task_id,
            subtask_id,
            task_owner,
            task_changed,
            subtask_userid,
            subtask_type,
            subtask_package,
            subtask_srpm_name,
            subtask_pkg_from
        FROM Tasks
        PREWHERE subtask_deleted = 0
        AND (task_id, task_changed) IN
        (
            SELECT
                task_id,
                task_changed
            FROM last_tasks
        )
    ) AS TSK USING (task_id,subtask_id, task_changed)
    PREWHERE (task_id, task_changed) IN
        (
            SELECT
                task_id,
                task_changed
            FROM last_tasks
        )
) AS RQ
LEFT JOIN
(
    SELECT * from last_tasks
) AS LST USING (task_id, task_changed)
ORDER BY task_changed DESC, subtask_id ASC
"""

    get_last_pkgs_info = """
SELECT DISTINCT
    pkg_hash,
    pkg_name,
    pkg_version,
    pkg_release,
    pkg_buildtime,
    pkg_summary,
    CHLG.chlog_name,
    CHLG.chlog_date,
    CHLG.chlog_text
FROM Packages
LEFT JOIN
(
    SELECT
        pkg_hash,
        chlog_name,
        chlog_date,
        chlog_text
    FROM SrcPackagesLastChangelog
    WHERE pkg_hash IN (
        SELECT pkg_hash
        FROM {tmp_table}
    )
) AS CHLG ON CHLG.pkg_hash = Packages.pkg_hash
WHERE
    pkg_hash IN
    (
        SELECT * FROM {tmp_table}
    )
"""

    get_last_branch_task_and_date = """
SELECT
    toUInt32(pkgset_kv.v[indexOf(pkgset_kv.k, 'task')]),
    pkgset_date
FROM PackageSetName
WHERE pkgset_nodename = '{branch}'
    AND pkgset_date = (
        SELECT DISTINCT pkgset_date
        FROM lv_pkgset_stat
        WHERE pkgset_name = '{branch}'
    )
"""

    get_tasks_by_maintainer = """
WITH tasks as (
SELECT
    task_id,
    arraySlice(
        splitByChar('|', search),
        1,
        4
    )[4] AS state,
    ts_ AS task_changed
FROM (
    SELECT toUInt32(lead)            AS task_id,
           argMax(search_string, ts) AS search,
           max(ts)                   AS ts_
    FROM GlobalSearch
    WHERE search_string ILIKE '{branch}|{maintainer_nickname}|%'
      AND type = 'task'
    GROUP BY lead
    ORDER BY max(ts) DESC
       )
WHERE search NOT LIKE '%|DELETED|%'
),
tasks_in_progress AS (
    SELECT DISTINCT task_id FROM TaskProgress
    WHERE task_id IN (SELECT task_id FROM tasks)
),
tasks_not_in_progress AS (
    SELECT DISTINCT task_id FROM Tasks
    WHERE task_id IN (SELECT task_id FROM tasks)
        AND task_id NOT IN tasks_in_progress
)
SELECT
    task_id,
    state,
    task_changed,
    groupUniqArray(tuple(T2.*)) AS gears
FROM tasks
LEFT JOIN
(
    SELECT
        task_id,
        subtask_id,
        argMax(repo, changed),
        argMax(owner, changed),
        argMax(sub_type, changed),
        argMax(dir, changed),
        argMax(tag_id, changed),
        argMax(srpm_name, changed),
        argMax(srpm_evr, changed),
        argMax(package, changed),
        argMax(pkg_from, changed),
        max(changed),
        argMax(srpm, changed)
    FROM (
        SELECT * FROM (
            SELECT
                task_id,
                subtask_id,
                argMax(task_repo, ts) AS repo,
                argMax(task_owner, ts) AS owner,
                argMax(subtask_type, ts) AS sub_type,
                argMax(subtask_srpm, ts) AS srpm,
                argMax(subtask_srpm_name, ts) AS srpm_name,
                argMax(subtask_srpm_evr, ts) AS srpm_evr,
                argMax(subtask_dir, ts) AS dir,
                argMax(subtask_tag_id, ts) AS tag_id,
                argMax(subtask_package, ts) AS package,
                argMax(subtask_pkg_from, ts) AS pkg_from,
                argMax(subtask_changed, ts) AS changed
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
                argMax(task_repo, ts) AS repo,
                argMax(task_owner, ts) AS owner,
                argMax(subtask_type, ts) AS sub_type,
                argMax(subtask_srpm, ts) AS srpm,
                argMax(subtask_srpm_name, ts) AS srpm_name,
                argMax(subtask_srpm_evr, ts) AS srpm_evr,
                argMax(subtask_dir, ts) AS dir,
                argMax(subtask_tag_id, ts) AS tag_id,
                argMax(subtask_package, ts) AS package,
                argMax(subtask_pkg_from, ts) AS pkg_from,
                argMax(subtask_changed, ts) AS changed
            FROM Tasks
            WHERE task_id IN tasks_not_in_progress
            GROUP BY task_id, subtask_id
        ) WHERE sub_type != 'unknown'
            OR arrayFilter(x -> notEmpty(x), [srpm, package, dir]) != []
    )
    GROUP BY task_id, subtask_id
    ORDER BY subtask_id
) AS T2 USING (task_id)
GROUP BY
    task_id,
    state,
    task_changed
ORDER BY task_changed DESC
"""

    get_all_src_versions_from_tasks = """
WITH
pkg_packages AS
(
    SELECT
        pkg_hash,
        pkg_name,
        pkg_version,
        pkg_release
    FROM Packages
    WHERE pkg_name = '{name}' AND pkg_sourcepackage = 1
),
pkg_tasks AS
(
    SELECT DISTINCT
        task_id,
        titer_srcrpm_hash
    FROM TaskIterations
    WHERE titer_srcrpm_hash IN (
        SELECT pkg_hash
        FROM pkg_packages
    )
        AND (task_id, task_changed) IN
        (
            SELECT
                task_id,
                task_changed
            FROM TaskStates
            WHERE task_state = 'DONE'
        )
)
SELECT DISTINCT
    pkg_tasks.task_id,
    toString(pkg_tasks.titer_srcrpm_hash),
    TSK.repo,
    TSK.owner,
    TSK.changed,
    PKG.pkg_name,
    PKG.pkg_version,
    PKG.pkg_release
FROM pkg_tasks
INNER JOIN
(
    SELECT
        task_id,
        any(task_repo) AS repo,
        any(task_owner) AS owner,
        max(task_changed) AS changed
    FROM Tasks
    {branch_sub}
    GROUP BY task_id
) AS TSK ON TSK.task_id = pkg_tasks.task_id
LEFT JOIN
(
    SELECT *
    FROM pkg_packages
) AS PKG ON pkg_hash = titer_srcrpm_hash
"""


sql = SQL()
