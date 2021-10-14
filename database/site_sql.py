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
WHERE pkgset_name = %(branch)s
    AND pkg_sourcepackage IN {src}
    AND pkg_buildtime >= %(buildtime)s
    AND pkg_name NOT LIKE '%%-debuginfo'
    {group}
ORDER BY pkg_name
"""

    get_pkg_changelog_old = """
SELECT changelog
FROM PackageChangelog_view
WHERE pkg_hash = {pkghash}
"""

    get_pkg_changelog = """
WITH pkg_changelog AS
    (
        SELECT
            pkg_hash,
            pkg_changelog.date AS date,
            pkg_changelog.name as name,
            pkg_changelog.evr AS evr,
            pkg_changelog.hash AS hash
        FROM repodb.Packages
ARRAY JOIN pkg_changelog
        WHERE pkg_hash = %(pkghash)s
    )
SELECT
    pkg_hash,
    date,
    name,
    evr,
    Chg.chlog_text as text
FROM pkg_changelog
LEFT JOIN
(
    SELECT DISTINCT
        chlog_hash AS hash,
        chlog_text
    FROM repodb.Changelog_buffer
    WHERE chlog_hash IN (
        SELECT hash
        FROM pkg_changelog
    )
) AS Chg ON Chg.hash = pkg_changelog.hash
ORDER BY
    date DESC,
    evr DESC
LIMIT %(limit)s
"""

    get_pkg_info = """
SELECT
    pkg_name,
    pkg_version,
    pkg_release,
    pkg_arch,
    pkg_epoch,
    pkg_buildtime,
    pkg_url,
    pkg_license,
    pkg_summary,
    pkg_description,
    pkg_packager,
    substring(pkg_packager_email, 1, position(pkg_packager_email, '@') - 1) AS packager_nick,
    pkg_group_
FROM Packages
WHERE pkg_hash = {pkghash}
    {source}
"""

    get_pkg_maintainers = """
SELECT pkg_changelog.name
FROM Packages
WHERE pkg_hash = {pkghash}
"""

    get_binary_pkgs = """
SELECT DISTINCT
    pkg_name,
    groupUniqArray((pkg_arch, pkg_hash))
FROM Packages
WHERE (pkg_srcrpm_hash = {pkghash})
    AND (pkg_sourcepackage = 0)
    AND pkg_arch IN
    (
        SELECT pkg_arch
        FROM lv_pkgset_stat
        WHERE pkgset_name = '{branch}'
    )
GROUP BY pkg_name
ORDER BY pkg_name ASC
"""

    get_source_pkgs = """
SELECT DISTINCT
    pkg_name,
    pkg_hash
FROM Packages
WHERE pkg_hash = (
    SELECT pkg_srcrpm_hash
    FROM Packages
    WHERE pkg_hash = {pkghash}
        AND pkg_sourcepackage = 0
    ORDER BY pkg_srcrpm_hash ASC
) AND pkg_sourcepackage = 1
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

    get_pkg_binary_versions = """
SELECT DISTINCT
    pkgset_name,
    pkg_version,
    pkg_release,
    toString(pkg_hash)
FROM last_packages
WHERE pkg_name = '{name}'
    AND pkg_arch = '{arch}'
    AND pkg_sourcepackage = 0
"""

    get_pkg_binary_list_versions = """
SELECT DISTINCT
    pkgset_name,
    pkg_version,
    pkg_release
FROM static_last_packages
WHERE pkg_name = '{name}'
    AND pkg_sourcepackage = 0
GROUP BY
    pkgset_name,
    pkg_version,
    pkg_release
"""

    get_pkg_versions_by_hash = """
SELECT DISTINCT
    pkgset_name,
    pkg_version,
    pkg_release,
    toString(pkg_hash)
FROM static_last_packages
WHERE pkg_name = (
    SELECT DISTINCT pkg_name
    FROM static_last_packages
    WHERE pkg_hash= {pkghash}
        AND pkg_sourcepackage = 1
)
    AND pkg_sourcepackage = 1
"""

    get_pkg_dependencies = """
SELECT
    dp_name,
    dp_version,
    dp_flag
FROM Depends
WHERE pkg_hash = {pkghash}
    AND dp_type = 'require'
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

    get_pkghash_by_binary_name = """
    SELECT DISTINCT
        pkg_hash,
        pkg_version,
        pkg_release
    FROM last_packages
    WHERE pkgset_name = '{branch}'
        AND pkg_name = '{name}'
        AND pkg_arch = '{arch}'
        AND pkg_sourcepackage = 0
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
SELECT groupUniqArray(pkgset_name)
FROM lv_pkgset_stat
"""

    get_all_pkgset_names_with_pkg_count = """
SELECT
    pkgset_name,
    cnt
FROM lv_pkgset_stat
WHERE pkg_arch = 'srpm'
"""

    get_all_bin_pkg_archs = """
SELECT groupUniqArray(pkg_arch)
FROM lv_pkgset_stat
WHERE pkgset_name = '{branch}'
"""

    get_all_src_cnt_by_bin_archs = """
SELECT
    pkg_arch,
    cnt
FROM lv_pkgset_stat
WHERE pkgset_name = '{branch}'
    AND pkg_arch NOT LIKE 'srpm'
"""

    get_all_pkgsets_with_src_cnt_by_bin_archs = """
SELECT
    pkgset_name,
    pkg_arch,
    cnt
FROM lv_pkgset_stat
"""

    get_pkgset_stat = """
SELECT
    pkgset_name,
    pkgset_date,
    pkg_arch,
    cnt
FROM lv_pkgset_stat
{where}
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
        WHERE task_repo = %(branch)s
            {task_owner_sub}
        ORDER BY task_changed DESC LIMIT %(limit2)s
    )
    AND task_state = 'DONE'
    ORDER BY
    task_changed DESC
    LIMIT %(limit)s
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
    pkg_changelog.name[1],
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

    get_last_branch_task = """
SELECT
    toUInt32(pkgset_kv.v[indexOf(pkgset_kv.k, 'task')])
FROM PackageSetName
WHERE pkgset_nodename = '{branch}'
    AND pkgset_date = (
        SELECT DISTINCT pkgset_date
        FROM lv_pkgset_stat
        WHERE pkgset_name = '{branch}'
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

    get_all_maintaners = """
SELECT
    argMax(pkg_packager, cnt) AS name,
    argMax(packager_nick, cnt) AS nick,
    sum(cnt) AS count
FROM
(
    SELECT DISTINCT
        pkg_packager,
        substring(pkg_packager_email, 1, position(pkg_packager_email, '@') - 1) AS packager_nick,
        countDistinct(pkg_hash) AS cnt
    FROM last_packages
    WHERE pkgset_name = '{branch}'
        AND pkg_sourcepackage = 1
    GROUP BY
        pkg_packager,
        packager_nick
)
{where_clause}
GROUP BY packager_nick ORDER by name
"""

    get_maintainer_branches = """
SELECT
    pkgset_name,
    countDistinct(pkg_hash)
FROM last_packages
WHERE pkg_packager_email LIKE '{maintainer_nickname}@%'
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
WHERE pkg_packager_email LIKE '{maintainer_nickname}@%'
    AND pkgset_name = '{branch}'
    AND pkg_sourcepackage = 1
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

    get_beehive_errors_by_maintainer = """
WITH
last_bh_updated AS
(
    SELECT
        pkgset_name,
        bh_arch as arch,
        max(bh_updated) AS updated
    FROM BeehiveStatus
    WHERE pkgset_name = '{branch}'
    GROUP BY
        pkgset_name,
        bh_arch
),
maintainer_packages AS
(
    SELECT
        pkg_hash,
        pkg_epoch
    FROM last_packages
    WHERE pkg_packager_email LIKE '{maintainer_nickname}@%'
        AND pkgset_name = '{branch}'
        AND pkg_sourcepackage = 1
)
SELECT
    pkg_hash,
    pkgset_name,
    pkg_name,
    pkg_version,
    pkg_release,
    bh_arch,
    bh_build_time,
    bh_updated,
    bh_ftbfs_since,
    Pkg.pkg_epoch
FROM BeehiveStatus
LEFT JOIN
(SELECT pkg_hash, pkg_epoch FROM maintainer_packages) AS Pkg USING (pkg_hash)
WHERE pkgset_name = '{branch}'
    AND bh_status = 'error'
    AND (bh_arch, bh_updated) IN
    (
        SELECT arch, updated FROM last_bh_updated
    )
    AND pkg_hash IN
    (
        SELECT pkg_hash FROM maintainer_packages
    )
ORDER BY pkg_name
"""

    get_deleted_package_task_by_src = """
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

    get_deleted_package_task_by_bin = """
WITH
(
    SELECT DISTINCT pkg_name
    FROM Packages
    WHERE pkg_hash IN
    (
        SELECT any(pkg_srcrpm_hash)
        FROM Packages
        WHERE pkg_name = '{name}'
        AND pkg_sourcepackage = 0
    ) AND pkg_sourcepackage = 1
) AS src_package
SELECT
    task_id,
    any(subtask_id),
    max(task_changed),
    any(task_owner),
    any(subtask_userid)
FROM Tasks
WHERE subtask_deleted = 0
    AND subtask_type = 'delete'
    AND subtask_package = src_package
    AND task_repo = '{branch}'
    AND task_id IN
    (
        SELECT task_id
        FROM TaskStates
        WHERE task_state = 'DONE'
    )
GROUP BY task_id
"""

    preselect_last_build_task_by_src = """
pkg_name = '{name}'
"""

    preselect_last_build_task_by_bin = """
pkg_hash IN
(
    SELECT pkg_srcrpm_hash
    FROM Packages
    WHERE pkg_name = '{name}'
        AND pkg_arch = '{arch}'
        AND pkg_sourcepackage = 0
)
"""

    get_last_build_task_by_pkg = """
WITH
src_pkg_hashes AS
(
    SELECT
        pkg_hash,
        pkg_version,
        pkg_release
    FROM Packages
    WHERE {preselect} AND pkg_sourcepackage = 1
)
SELECT DISTINCT
    task_id,
    titer_srcrpm_hash,
    PI.pkg_version,
    PI.pkg_release
FROM TaskIterations
LEFT JOIN
(
    SELECT
        pkg_hash,
        pkg_version,
        pkg_release
    FROM src_pkg_hashes
) AS PI ON PI.pkg_hash = titer_srcrpm_hash
WHERE titer_srcrpm_hash IN
    (
        SELECT pkg_hash FROM src_pkg_hashes
    )
    AND (task_id, subtask_id) IN
    (
        SELECT
            task_id, subtask_id
        FROM Tasks
        WHERE task_repo = '{branch}'
            AND subtask_deleted = 0
            AND task_id IN
            (
                SELECT task_id
                FROM TaskStates
                WHERE task_state = 'DONE'
            )
    )
    AND task_changed < '{task_changed}'
ORDER BY task_changed DESC LIMIT 1
"""

    get_delete_task_message = """
SELECT task_message
FROM TaskStates
WHERE task_id = {task_id} AND task_changed = '{task_changed}'
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

    get_binpkg_hash_for_branch_on_date = """
SELECT
    pkg_hash,
    pkg_version,
    pkg_release
FROM Packages
WHERE pkg_hash IN (
    SELECT pkg_hash
    FROM PackageSet
    WHERE pkg_hash IN (
        SELECT pkg_hash
        FROM Packages
        WHERE pkg_name = '{name}'
            AND pkg_arch = '{arch}'
            AND pkg_sourcepackage = 0
    ) AND pkgset_uuid IN (
        SELECT pkgset_uuid
        FROM PackageSetName
        WHERE pkgset_depth = 2 AND pkgset_ruuid IN (
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

    get_last_packages_with_cve_fixes = """
WITH
changelog_with_cve AS
(
    SELECT DISTINCT
        chlog_hash,
        chlog_text
    FROM Changelog
    WHERE match(chlog_text, 'CVE-\d{{4}}-(\d{{7}}|\d{{6}}|\d{{5}}|\d{{4}})')
),
(
    SELECT groupUniqArray(chlog_hash)
    FROM changelog_with_cve
) AS changelog_hashes
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
    SELECT * FROM changelog_with_cve
) AS CHLG ON CHLG.chlog_hash = (pkg_changelog.hash[1])
WHERE pkg_hash IN
(
    SELECT pkg_hash
    FROM static_last_packages
    WHERE pkgset_name = '{branch}'
        AND pkg_sourcepackage = 1
)
    AND has(changelog_hashes, pkg_changelog.hash[1])
ORDER BY pkg_buildtime DESC
"""

    get_last_bh_rebuild_status_by_hsh = """
WITH
last_bh_updated AS
(
    SELECT
        pkgset_name,
        bh_arch as arch,
        max(bh_updated) AS updated
    FROM BeehiveStatus
    WHERE pkgset_name = %(branch)s
    GROUP BY
        pkgset_name,
        bh_arch
)
SELECT
    bh_arch,
    bh_status,
    bh_build_time,
    bh_updated,
    bh_ftbfs_since
FROM BeehiveStatus
WHERE pkgset_name = %(branch)s
    AND pkg_hash = %(pkghash)s
    AND (bh_arch, bh_updated) IN
    (
        SELECT arch, updated FROM last_bh_updated
    )
"""

    get_build_task_by_hash = """
SELECT
    task_id,
    subtask_id,
    subtask_arch,
    titer_srcrpm_hash,
    titer_pkgs_hash
FROM TaskIterations
WHERE (task_id, task_changed) IN
(
    SELECT
    argMax(task_id, task_changed),
    max(task_changed)
    FROM TaskIterations
    WHERE titer_srcrpm_hash = {pkghash} AND task_id IN
    (
        SELECT task_id
        FROM TaskStates
        WHERE task_state = 'DONE'
    )
)
    AND titer_srcrpm_hash = {pkghash}
    AND
    (
        SELECT count(task_id)
        FROM Tasks
        WHERE task_repo = '{branch}'
    ) != 0
"""

    get_src_and_binary_pkgs = """
SELECT DISTINCT
    pkg_hash,
    pkg_filename,
    pkg_arch,
    pkg_filesize
FROM last_packages
WHERE pkg_srcrpm_hash = {pkghash} AND pkgset_name = '{branch}'
"""

    get_pkgs_filename_by_hshs = """
SELECT
    pkg_hash,
    pkg_filename,
    pkg_arch,
    pkg_filesize
FROM Packages
WHERE pkg_hash IN {hshs}
"""

    get_pkgs_md5_by_hshs = """
SELECT
    pkgh_mmh,
    pkgh_md5
FROM PackageHash_view
WHERE pkgh_mmh IN {hshs}
"""

    get_pkgs_binary_list = """
SELECT DISTINCT
    pkg_hash,
    pkg_name,
    pkg_version,
    pkg_release,
    pkg_arch
FROM last_packages
WHERE pkgset_name = '{branch}'
    AND pkg_name = '{name}'
    AND pkg_sourcepackage = 0
"""

    get_last_branch_src_diff = """
CREATE TEMPORARY TABLE {tmp_table} AS
SELECT pkg_hash FROM
(
    WITH
    (
        SELECT DISTINCT pkgset_date
        FROM lv_pkgset_stat
        WHERE pkgset_name = '{branch}'
    ) AS last_pkgset_date
    SELECT DISTINCT pkg_hash
    FROM static_last_packages
    WHERE pkgset_name = '{branch}'
        AND pkg_sourcepackage = 1
        AND pkg_hash NOT IN
        (
            SELECT pkg_hash
            FROM PackageSet
            WHERE pkgset_uuid = (
                SELECT pkgset_uuid
                FROM PackageSetName
                WHERE pkgset_nodename = 'srpm'
                    AND pkgset_ruuid = (
                        SELECT argMax(pkgset_ruuid, pkgset_date)
                        FROM PackageSetName
                        WHERE pkgset_depth = 0
                            AND pkgset_nodename = '{branch}'
                            AND pkgset_date < last_pkgset_date
                    )
            )
        )
)
"""

    get_last_branch_hsh_source = """
static_last_packages
WHERE pkgset_name = '{branch}'
    AND pkg_sourcepackage = 1
"""

    get_last_branch_pkgs_info = """
SELECT * FROM
(
    SELECT DISTINCT
        pkg_hash,
        pkg_name,
        pkg_version,
        pkg_release,
        pkg_summary,
        pkg_changelog.name[1],
        pkg_changelog.date[1],
        CHLG.chlog_text
    FROM Packages
    LEFT JOIN
    (
        SELECT
            pkg_hash,
            chlog_text
        FROM mv_src_packages_last_changelog
        WHERE pkg_hash IN (
            SELECT pkg_hash
            FROM {hsh_source}
        )
    ) AS CHLG ON CHLG.pkg_hash = Packages.pkg_hash
    WHERE
        pkg_hash IN
        (
            SELECT pkg_hash FROM {hsh_source}
        )
    {packager}
    LIMIT {limit}
) AS RQ
LEFT JOIN
(
    SELECT
        pkg_srcrpm_hash AS hash,
        max(pkg_buildtime) AS last_build
    FROM Packages
    WHERE pkg_sourcepackage = 0
    GROUP BY pkg_srcrpm_hash
) AS BinLastBuild ON BinLastBuild.hash = RQ.pkg_hash
ORDER BY last_build DESC
"""


sitesql = SQL()
