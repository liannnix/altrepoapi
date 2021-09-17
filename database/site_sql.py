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
    FROM Changelog
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
FROM Packages
WHERE pkg_hash = {pkghash}
"""

    get_pkg_maintaners = """
SELECT DISTINCT
    pkg_packager,
    pkg_packager_email
FROM Packages
WHERE pkg_name = '{name}'
    AND pkg_sourcepackage = 1
"""

    get_binary_pkgs = """
SELECT DISTINCT pkg_name
FROM Packages
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
FROM TaskIterations
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
FROM Tasks
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
FROM Tasks
WHERE (task_id, subtask_id) IN
(
    SELECT
        task_id,
        subtask_id
    FROM TaskIterations
    WHERE titer_srcrpm_hash = {pkghash}
)
AND task_id IN
(
    SELECT task_id
    FROM TaskStates
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
    pkg_name
FROM TaskIterations
LEFT JOIN
(
    SELECT
        pkg_hash,
        pkg_name
    FROM Packages
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
FROM Packages
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
FROM Packages
INNER JOIN lp_preselect2 AS LP2 USING (pkg_hash)
WHERE pkg_name NOT ILIKE '%{name}%'
    AND pkg_sourcepackage = 1
    AND pkg_sourcerpm IN 
    (
        SELECT pkg_sourcerpm
        FROM Packages
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
FROM Packages
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
    FROM Packages
    WHERE pkg_sourcepackage = 1
) AS P ON P.pkg_hash = last_packages.pkg_srcrpm_hash
WHERE pkg_sourcepackage = 0
    AND pkg_arch != 'x86_64-i586'
    AND pkgset_name = '{branch}'
GROUP BY pkg_arch
"""

    get_last_subtasks_from_tasks = """
WITH
last_tasks AS
(
    SELECT DISTINCT
        task_id ,
        task_changed,
        task_message
    FROM TaskStates
    WHERE task_id IN
    (
        SELECT DISTINCT task_id
        FROM Tasks
        WHERE task_repo = '{branch}'
        ORDER BY task_changed DESC LIMIT {limit2}
    )
    AND task_state = 'DONE'
    ORDER BY
    task_changed DESC
    LIMIT {limit}
)
SELECT * FROM
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
            subtask_srpm_name
        FROM
            Tasks
        PREWHERE subtask_deleted = 0
        AND (task_id, task_changed) IN
        (
            SELECT
                task_id,
                task_changed
            FROM last_tasks
        )
    ) AS TSK USING (task_id,subtask_id, task_changed)
    PREWHERE titer_srcrpm_hash != 0
        AND (task_id, task_changed) IN
        (
            SELECT
                task_id,
                task_changed
            FROM last_tasks
        )
    ORDER BY task_changed DESC, subtask_id ASC
) AS RQ
LEFT JOIN
(
    SELECT * from last_tasks
) AS LST USING (task_id, task_changed)
"""

    get_last_pkgs_info = """
SELECT DISTINCT
    pkg_hash,
    pkg_name,
    pkg_version,
    pkg_release,
    pkg_buildtime,
    pkg_summary,
    pkg_changelog.date[1],
    CHLG.chlog_text
FROM Packages
LEFT JOIN 
(
    SELECT
        chlog_hash,
        chlog_text
    FROM Changelog
) AS CHLG ON CHLG.chlog_hash = (pkg_changelog.hash[1])
WHERE
    pkg_hash IN
    (
        SELECT * FROM {tmp_table}
    )
"""

    get_pkgset_groups_count = """
SELECT
    pkg_group_,
    count(pkg_hash)
FROM Packages
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

    get_all_maintainers_with_emails = """
SELECT
    pkg_packager,
    pkg_packager_email,
    countDistinct(pkg_hash) as cnt
FROM last_packages
WHERE pkg_sourcepackage = 1
    AND pkgset_name = '{branch}'
GROUP BY
    pkg_packager,
    pkg_packager_email
"""

    get_all_maintaners_with_nicknames = """
SELECT
    any(pkg_packager) AS name,
    argMax(email, cnt) as email,
    argMax(packager_nick, cnt) AS nick,
    any(cnt) AS count
FROM
(
    SELECT DISTINCT
        pkg_packager,
        substring(pkg_packager_email, 1, position(pkg_packager_email, '@') - 1) AS packager_nick,
        any(pkg_packager_email) as email,
        countDistinct(pkg_hash) AS cnt
    FROM last_packages
    WHERE pkgset_name = '{branch}'
        AND pkg_sourcepackage = 1
    GROUP BY
        pkg_packager,
        packager_nick
)
GROUP BY packager_nick ORDER by name
"""

    get_maintainer_info = """
SELECT
    groupUniqArray(pkg_packager),
    groupUniqArray(pkg_packager_email),
    toDateTime(max(pkg_buildtime)),
    countIf(pkg_sourcepackage, pkg_sourcepackage=1) as src,
    countIf(pkg_sourcepackage, pkg_sourcepackage=0) as bin
FROM last_packages
WHERE (pkg_packager_email LIKE '{maintainer_nickname}@%'
    OR pkg_packager_email LIKE '{maintainer_nickname} at%'
    OR pkg_packager LIKE '%{maintainer_nickname}@%')
    AND pkgset_name = '{branch}'
"""

    get_maintainer_branches = """
SELECT
    pkgset_name,
    countDistinct(pkg_hash)
FROM last_packages
WHERE (pkg_packager_email LIKE '{maintainer_nickname}@%' 
    OR pkg_packager_email LIKE '{maintainer_nickname} at%'
    OR pkg_packager LIKE '%{maintainer_nickname}@%')
    AND pkg_sourcepackage = 1
GROUP BY
    pkgset_name    
"""

    get_maintainer_pkg = """
SELECT
    pkg_name,
    pkg_buildtime,
    pkg_url,
    pkg_summary,
    pkg_version,
    pkg_release
FROM last_packages
WHERE (pkg_packager_email LIKE '{maintainer_nickname}@%' 
    OR pkg_packager_email LIKE '{maintainer_nickname} at%'
    OR pkg_packager LIKE '%{maintainer_nickname}@%')
    and pkgset_name = '{branch}'
    and pkg_sourcepackage = 1
GROUP BY
    pkg_name,
    pkg_version,
    pkg_release,
    pkg_buildtime,
    pkg_url,
    pkg_summary
ORDER BY pkg_buildtime DESC
"""

    get_tasks_by_maintainer = """
SELECT
    T1.*,
    groupUniqArray(tuple(T2.*)) AS gears
FROM
(
    SELECT DISTINCT
        task_id,
        TS.task_state,
        TS.changed AS task_changed
    FROM Tasks
    LEFT JOIN
    (
        SELECT
            task_id,
            argMax(task_state, task_changed) AS task_state,
            max(task_changed) AS changed
        FROM TaskStates
        GROUP BY task_id
    ) AS TS USING (task_id)
    WHERE task_owner = '{maintainer_nickname}'
    AND task_repo = '{branch}'
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

    get_src_pkg_ver_rel_maintainer = """
SELECT
    pkgset_name,
    pkg_name,
    pkg_version,
    pkg_release
FROM last_packages
WHERE (pkg_packager_email LIKE '{maintainer_nickname}@%' 
    OR pkg_packager_email LIKE '{maintainer_nickname} at%'
    OR pkg_packager LIKE '%{maintainer_nickname}@%')
    and pkgset_name = '{branch}'
    and pkg_sourcepackage = 1
GROUP BY
    pkgset_name,
    pkg_name,
    pkg_version,
    pkg_release
"""

    get_repocop_by_maintainer = """
SELECT
    pkg_name,
    pkg_version,
    pkg_release,
    pkg_arch,
    rc_srcpkg_name,
    pkgset_name,
    rc_test_name,
    argMax(rc_test_status, rc_test_date),
    argMax(rc_test_message, rc_test_date),
    max(rc_test_date)
FROM PackagesRepocop
WHERE rc_test_status NOT IN ('ok', 'skip')
    AND (rc_srcpkg_name, rc_srcpkg_version, rc_srcpkg_release, pkgset_name) IN 
(SELECT * FROM {tmp_table})
GROUP BY
    pkg_name,
    pkg_version,
    pkg_release,
    pkg_arch,
    rc_srcpkg_name,
    pkgset_name,
    rc_test_name
ORDER BY
    pkg_name ASC,
    pkg_arch ASC    
"""

    get_deleted_package_task = """
SELECT
    task_id,
    any(subtask_id),
    max(task_changed),
    any(task_owner),
    any(subtask_userid)
FROM Tasks
WHERE subtask_deleted = 0
    AND subtask_type = 'delete'
    AND subtask_package = '{name}'
    AND task_repo = '{branch}'
    AND task_id IN
    (
        SELECT task_id
        FROM TaskStates
        WHERE task_state = 'DONE'
    )
GROUP BY task_id
"""

    get_srcpkg_hash_for_branch_on_date = """
SELECT
    pkg_hash,
    pkg_version,
    pkg_release
FROM Packages
WHERE pkg_hash IN
(
    SELECT pkg_hash
    FROM PackageSet
    WHERE pkg_hash IN (
        SELECT pkg_hash
        FROM Packages
        WHERE pkg_name = '{name}' AND pkg_sourcepackage = 1
    ) AND pkgset_uuid IN (
        SELECT pkgset_uuid
        FROM PackageSetName
        WHERE pkgset_nodename = 'srpm' AND pkgset_ruuid IN (
            SELECT argMax(pkgset_uuid, pkgset_date)
            FROM PackageSetName
            WHERE pkgset_nodename = '{branch}'
                AND toDate(pkgset_date) <= (toDate('{task_changed}') - 1)
        )
    )
)
"""

    get_last_scrpkg_hash_in_branch = """
WITH
all_src_hashes AS
(
    SELECT pkg_hash
    FROM Packages
    WHERE pkg_name like '{name}'
        AND pkg_sourcepackage = 1
)
SELECT DISTINCT pkg_hash
FROM PackageSet
WHERE pkgset_uuid IN
(
    SELECT pkgset_uuid
    FROM PackageSetName
    WHERE pkgset_nodename = 'srpm'
        AND pkgset_puuid IN
        (
            SELECT p_uuid FROM
            (
                SELECT
                    pkgset_nodename, max(pkgset_date) as p_date, argMax(pkgset_uuid, pkgset_date) as p_uuid
                FROM PackageSetName
                WHERE pkgset_uuid IN
                (
                    SELECT pkgset_ruuid
                    FROM PackageSetName
                    WHERE pkgset_uuid IN
                    (
                        SELECT pkgset_uuid
                        FROM PackageSet
                        WHERE pkg_hash IN all_src_hashes
                    )
                )
                    AND pkgset_nodename = '{branch}'
                GROUP BY pkgset_nodename
            )
        )
) AND pkg_hash IN all_src_hashes
"""


sitesql = SQL()
