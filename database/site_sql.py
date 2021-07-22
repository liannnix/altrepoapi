from dataclasses import dataclass

@dataclass(frozen=True)
class SQL:
    create_tmp_table = """
CREATE TEMPORARY TABLE {tmp_table} {columns}
"""

    select_all_tmp_table = """
SELECT * FROM {tmp_table}
"""

    get_repo_packages = """
SELECT
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
FROM last_packages
WHERE pkg_name = '{name}'
    AND pkg_sourcepackage = 1
"""

    get_pkg_task_by_hash = """
SELECT DISTINCT task_id
FROM TaskIterations_buffer
WHERE titer_srcrpm_hash = {pkghash}
"""

    get_pkghash_by_name = """
SELECT DISTINCT pkg_hash
FROM last_packages
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
        task_repo,
        task_owner,
        subtask_type,
        subtask_dir,
        subtask_srpm_name,
        subtask_package
    FROM Tasks_buffer
    WHERE subtask_deleted = 0
) AS T2 USING (task_id)
GROUP BY
    task_id,
    task_state,
    task_changed
ORDER BY task_changed DESC
"""

    get_find_packages_by_name = """
SELECT
    pkg_name,
    groupUniqArray((pkgset_name, pkg_version, pkg_release, toString(pkg_hash))),
    max(pkg_buildtime),
    argMax(pkg_url, pkg_buildtime),
    argMax(pkg_summary, pkg_buildtime),
    any(pkg_group_)
FROM last_packages
WHERE pkg_name LIKE '%{name}%'
    AND pkg_sourcepackage = 1
    {branch}
GROUP BY pkg_name
ORDER BY pkg_name
UNION ALL
SELECT
    pkg_name,
    groupUniqArray((pkgset_name, pkg_version, pkg_release, toString(pkg_hash))),
    max(pkg_buildtime),
    argMax(pkg_url, pkg_buildtime),
    argMax(pkg_summary, pkg_buildtime),
    any(pkg_group_)
FROM last_packages
WHERE pkg_name NOT LIKE '%{name}%'
    AND pkg_sourcepackage = 1
    {branch}
    AND pkg_sourcerpm IN 
(
    SELECT pkg_sourcerpm
    FROM Packages_buffer
    WHERE pkg_sourcepackage = 0
        AND pkg_name LIKE '%{name}%'
        {arch}
)
GROUP BY pkg_name
ORDER BY pkg_name
"""


sitesql = SQL()
