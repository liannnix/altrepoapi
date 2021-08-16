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

    get_repo_packages = """
SELECT DISTINCT
    toString(pkg_hash),
    pkg_name,
    pkg_version,
    pkg_release,
    pkg_buildtime,
    pkg_summary,
    pkg_packager_email,
    pkg_group_,
    CHLG.chlog_text
FROM last_packages
LEFT JOIN 
(
    SELECT
        chlog_hash,
        chlog_text
    FROM Changelog_buffer
) AS CHLG ON CHLG.chlog_hash = (pkg_changelog.hash[1])
WHERE pkgset_name = '{branch}'
    AND pkg_sourcepackage IN {src}
    AND pkg_buildtime >= {buildtime}
    AND pkg_name NOT LIKE '%%-debuginfo'
    {group}
ORDER BY pkg_name
"""

    get_pkg_changelog = """
SELECT changelog
FROM PackageChangelog_view
WHERE pkg_hash = {pkghash}
"""

    get_pkg_info = """
SELECT
    pkg_name,
    pkg_version,
    pkg_release,
    pkg_buildtime,
    pkg_url,
    pkg_license,
    pkg_summary,
    pkg_description,
    pkg_packager,
    pkg_packager_email,
    pkg_group_
FROM Packages_buffer
WHERE pkg_hash = {pkghash}
"""

    get_pkg_maintaners = """
SELECT DISTINCT
    pkg_packager,
    pkg_packager_email
FROM Packages_buffer
WHERE pkg_name = '{name}'
    AND pkg_sourcepackage = 1
"""

    get_binary_pkgs = """
SELECT DISTINCT pkg_name
FROM Packages_buffer
WHERE pkg_srcrpm_hash = {pkghash}
    AND pkg_sourcepackage = 0
ORDER BY pkg_name ASC
"""

    get_pkg_acl = """
SELECT acl_list
FROM Acl
WHERE acl_for = '{name}'
    AND acl_branch = '{branch}'
"""

    get_pkg_versions = """
SELECT DISTINCT
    pkgset_name,
    pkg_version,
    pkg_release,
    toString(pkg_hash)
FROM static_last_packages
WHERE pkg_name = '{name}'
    AND pkg_sourcepackage = 1
"""

    get_pkg_task_by_hash = """
SELECT DISTINCT
    task_id,
    subtask_id
FROM TaskIterations_buffer
WHERE titer_srcrpm_hash = {pkghash}
    AND task_id IN 
    (
        SELECT task_id
        FROM Tasks
        WHERE task_repo = '{branch}'
    )
ORDER BY task_changed DESC
"""

    get_task_gears_by_id = """
SELECT DISTINCT
    subtask_type,
    subtask_dir,
    subtask_srpm_name,
    subtask_pkg_from
FROM Tasks_buffer
WHERE task_id = {task} AND subtask_id = {subtask}
"""

    get_task_gears_by_hash = """
SELECT DISTINCT
    task_repo,
    task_id,
    subtask_id,
    subtask_type,
    subtask_dir,
    subtask_tag_id,
    subtask_srpm_name,
    subtask_srpm_evr
FROM Tasks_buffer
WHERE (task_id, subtask_id) IN
(
    SELECT
        task_id,
        subtask_id
    FROM TaskIterations_buffer
    WHERE titer_srcrpm_hash = {pkghash}
)
AND task_id IN
(
    SELECT task_id
    FROM TaskStates_buffer
    WHERE task_state = 'DONE'
)
ORDER BY task_changed DESC
"""

    get_pkghash_by_name = """
SELECT DISTINCT
    pkg_hash,
    pkg_version,
    pkg_release
FROM static_last_packages
WHERE pkgset_name = '{branch}'
    AND pkg_name = '{name}'
    AND pkg_sourcepackage = 1
"""

    get_tasks_by_pkg_name = """
SELECT
    T1.*,
    groupUniqArray(tuple(T2.*)) AS gears
FROM 
(
    SELECT DISTINCT
        task_id,
        TS.task_state,
        TS.changed AS task_changed
    FROM TaskIterations
    LEFT JOIN 
    (
        SELECT
            task_id,
            argMax(task_state, task_changed) AS task_state,
            max(task_changed) AS changed
        FROM TaskStates_buffer
        GROUP BY task_id
    ) AS TS USING (task_id)
    WHERE titer_srcrpm_hash IN 
    (
        SELECT pkg_hash
        FROM Packages_buffer
        WHERE pkg_name LIKE '{name}'
            AND pkg_sourcepackage = 1
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
    FROM Tasks_buffer
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
    pkg_name
FROM TaskIterations_buffer
LEFT JOIN
(
    SELECT
        pkg_hash,
        pkg_name
    FROM Packages_buffer
    WHERE pkg_sourcepackage = 1
) AS P ON (pkg_hash = titer_srcrpm_hash)
WHERE (task_id, subtask_id) IN
(
    SELECT * FROM {tmp_table}
)
"""

    get_find_packages_by_name = """
WITH
lp_preselect AS
(
    SELECT
        pkg_hash,
        pkgset_name
    FROM static_last_packages
    WHERE pkg_name ILIKE '%{name}%'
        AND pkg_sourcepackage = 1
        {branch}
),
lp_preselect2 AS
(
    SELECT
        pkg_hash,
        pkgset_name
    FROM static_last_packages
    WHERE pkg_name NOT ILIKE '%{name}%'
        AND pkg_sourcepackage = 1
        {branch}
)
SELECT
    pkg_name,
    groupUniqArray((LP.pkgset_name, pkg_version, pkg_release, toString(pkg_hash))),
    max(pkg_buildtime),
    argMax(pkg_url, pkg_buildtime),
    argMax(pkg_summary, pkg_buildtime),
    any(pkg_group_)
FROM Packages_buffer
INNER JOIN lp_preselect AS LP USING (pkg_hash)
WHERE pkg_hash IN
(
    SELECT pkg_hash FROM lp_preselect
)
GROUP BY pkg_name
ORDER BY pkg_name
UNION ALL
SELECT
    pkg_name,
    groupUniqArray((LP2.pkgset_name, pkg_version, pkg_release, toString(pkg_hash))),
    max(pkg_buildtime),
    argMax(pkg_url, pkg_buildtime),
    argMax(pkg_summary, pkg_buildtime),
    any(pkg_group_)
FROM Packages_buffer
INNER JOIN lp_preselect2 AS LP2 USING (pkg_hash)
WHERE pkg_name NOT ILIKE '%{name}%'
    AND pkg_sourcepackage = 1
    AND pkg_sourcerpm IN 
    (
        SELECT pkg_sourcerpm
        FROM Packages_buffer
        WHERE pkg_sourcepackage = 0
            AND pkg_name ILIKE '%{name}%'
            {arch}
    )
    {branch}
GROUP BY pkg_name
ORDER BY pkg_name
"""

    get_all_pkgset_names = """
SELECT groupUniqArray(pkgset_nodename)
FROM PackageSetName
WHERE pkgset_depth = 0
"""

    get_all_pkgset_names_with_pkg_count = """
SELECT
    pkgset_name,
    count(pkg_hash)
FROM static_last_packages
WHERE pkg_sourcepackage = 1
GROUP BY pkgset_name
"""

    get_all_bin_pkg_archs = """
SELECT groupUniqArray(pkg_arch)
FROM Packages_buffer
WHERE pkg_sourcepackage = 0
    AND pkg_hash IN
    (
        SELECT pkg_hash
        FROM static_last_packages
        WHERE pkg_sourcepackage = 0
            AND pkgset_name = '{branch}'
    )
"""

    get_all_src_cnt_by_bin_archs = """
SELECT
    pkg_arch,
    countDistinct(src_pkg_name)
FROM last_packages
LEFT JOIN 
(
    SELECT
        pkg_hash,
        pkg_name AS src_pkg_name
    FROM Packages_buffer
    WHERE pkg_sourcepackage = 1
) AS P ON P.pkg_hash = last_packages.pkg_srcrpm_hash
WHERE pkg_sourcepackage = 0
    AND pkg_arch != 'x86_64-i586'
    AND pkgset_name = '{branch}'
GROUP BY pkg_arch
"""

    get_last_pkgs_from_tasks = """
WITH
(
    SELECT (task_changed - {timedelta}) as t
    FROM Tasks_buffer
    WHERE task_repo = '{branch}'
        AND task_id IN
        (
            SELECT task_id
            FROM TaskStates_buffer
            WHERE (task_state = 'DONE')
        )
    ORDER BY task_changed DESC
    LIMIT 1
) as task_build_start
SELECT DISTINCT
    toString(pkg_hash),
    pkg_name,
    pkg_version,
    pkg_release,
    pkg_buildtime,
    pkg_summary,
    pkg_packager_email,
    pkg_group_,
    CHLG.chlog_text
FROM Packages_buffer
LEFT JOIN 
(
    SELECT
        chlog_hash,
        chlog_text
    FROM Changelog_buffer
) AS CHLG ON CHLG.chlog_hash = (pkg_changelog.hash[1])
WHERE
    pkg_hash IN
(
    SELECT
        argMax(titer_srcrpm_hash, task_changed)
    FROM TaskIterations_buffer
    WHERE ((task_id, task_changed) IN 
    (
        SELECT
            argMax(task_id, task_changed),
            max(task_changed)
        FROM TaskStates_buffer
        INNER JOIN 
        (
            SELECT DISTINCT task_id
            FROM Tasks_buffer
            WHERE task_repo = '{branch}'
        ) AS T USING (task_id)
        WHERE (task_state = 'DONE') AND (task_changed >= task_build_start)
        GROUP BY task_id
    )) AND (titer_srcrpm_hash != 0)
    GROUP BY
        task_id,
        subtask_id
)
ORDER BY
    pkg_buildtime DESC
"""

    get_pkgset_groups_count = """
SELECT
    pkg_group_,
    count(pkg_hash)
FROM Packages_buffer
WHERE pkg_hash IN
(
    SELECT pkg_hash
    FROM static_last_packages
    WHERE pkgset_name = '{branch}'
        AND pkg_sourcepackage IN {sourcef}
        AND pkg_name NOT LIKE '%%-debuginfo'
    
)
GROUP BY pkg_group_
ORDER BY pkg_group_ ASC
"""

    get_all_pkgsets_by_hash = """
SELECT DISTINCT pkgset_nodename
FROM PackageSetName
WHERE (pkgset_ruuid IN 
(
    SELECT pkgset_ruuid
    FROM PackageSetName
    WHERE pkgset_uuid IN 
    (
        SELECT pkgset_uuid
        FROM PackageSet
        WHERE pkg_hash = {pkghash}
    )
)) AND (pkgset_depth = 0)
"""

    get_all_maintainers = """
SELECT
    pkg_packager,
    countDistinct(pkg_hash)
FROM last_packages
WHERE pkg_sourcepackage = 1
    and pkgset_name = '{branch}'
GROUP BY
    pkg_packager
"""

    get_maintainer_info = """
SELECT
    any(pkg_packager),
    argMax(pkg_packager_email, pkg_buildtime),
    toDateTime(max(pkg_buildtime)),
    countIf(pkg_sourcepackage, pkg_sourcepackage=1) as src,
    countIf(pkg_sourcepackage, pkg_sourcepackage=0) as bin
from last_packages
where pkg_packager like '{pkg_packager}'
and pkgset_name = '{branch}'
"""

sitesql = SQL()
