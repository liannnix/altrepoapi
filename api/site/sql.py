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
        pkg_hash,
        chlog_text
    FROM mv_src_packages_last_changelog
    ) AS CHLG ON CHLG.pkg_hash = last_packages.pkg_hash
WHERE pkgset_name = %(branch)s
    AND pkg_sourcepackage IN {src}
    AND pkg_buildtime >= %(buildtime)s
    AND pkg_name NOT LIKE '%%-debuginfo'
    {group}
ORDER BY pkg_name
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

    get_last_branch_date = """
SELECT DISTINCT pkgset_date
FROM lv_pkgset_stat
WHERE pkgset_name = '{branch}'
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

    get_pkgs_bin_depends = """
    SELECT
        dp_name,
        dp_version,
        dp_flag,
        dp_type
    FROM Depends
    WHERE pkg_hash = {pkghash}
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
        CHLG.chlog_name,
        CHLG.chlog_nick,
        CHLG.chlog_date,
        CHLG.chlog_text
    FROM Packages
    LEFT JOIN
    (
        SELECT
            pkg_hash,
            chlog_name,
            chlog_nick,
            chlog_date,
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
) AS RQ
LEFT JOIN
(
    SELECT
        pkg_srcrpm_hash AS hash,
        max(pkg_buildtime) AS last_build
    FROM Packages
    WHERE pkg_sourcepackage = 0
        AND pkg_hash IN
        (
            SELECT pkg_hash
            FROM static_last_packages
            WHERE pkgset_name = '{branch}'
                AND pkg_sourcepackage = 0
        )
    GROUP BY pkg_srcrpm_hash
) AS BinLastBuild ON BinLastBuild.hash = RQ.pkg_hash
ORDER BY last_build DESC
LIMIT {limit}
"""

    get_pkgset_status = """
SELECT
    pkgset_name,
    argMax(rs_start_date, ts) AS start_date,
    argMax(rs_end_date, ts) AS end_date,
    argMax(rs_show, ts) AS show,
    argMax(rs_description_ru, ts) AS desc_ru,
    argMax(rs_description_en, ts) AS desc_en
FROM RepositoryStatus
GROUP BY pkgset_name
"""


sql = SQL()
