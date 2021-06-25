from dataclasses import dataclass

@dataclass(frozen=True)
class SQL:
    create_tmp_table = """
CREATE TEMPORARY TABLE {tmp_table} {columns}
"""


    insert_build_req_deep_1 = """
INSERT INTO {tmp_table}
SELECT DISTINCT pkg_name
FROM Packages_buffer
WHERE 
(
    pkg_filename IN
    (
        SELECT DISTINCT if(pkg_sourcepackage = 1, pkg_filename, pkg_sourcerpm) AS sourcerpm
        FROM Packages_buffer
        WHERE pkg_hash IN
        (
            SELECT DISTINCT pkg_hash
            FROM last_depends
            WHERE dp_name IN
            (
                SELECT dp_name
                FROM Depends_buffer
                WHERE pkg_hash IN
                (
                    SELECT pkg_hash
                    FROM last_packages_with_source
                    WHERE sourcepkgname IN %(pkgs)s
                        AND pkgset_name = %(branch)s
                        AND pkg_arch IN ('x86_64', 'noarch')
                        AND pkg_name NOT LIKE '%%-debuginfo'
                )
                    AND dp_type = 'provide'
            )
                AND pkgset_name = %(branch)s
                AND pkg_sourcepackage IN %(sfilter)s
                AND dp_type = 'require'
                AND pkg_name NOT LIKE '%%-debuginfo'
        )
    )
)
    AND pkg_sourcepackage = 1
UNION ALL
SELECT arrayJoin(%(union)s)
"""

    increase_depth_wrap = """
SELECT pkg_hash
FROM last_depends
WHERE dp_name IN
(
    SELECT dp_name
    FROM Depends
    WHERE pkg_hash IN
    (
        SELECT pkg_hash
        FROM last_packages_with_source
        WHERE sourcepkgname IN
        (
            SELECT *
            FROM {tmp_table}
        )
            AND pkgset_name = %(branch)s
            AND pkg_arch IN ('x86_64', 'noarch')
            AND pkg_name NOT LIKE '%%-debuginfo'
    )
        AND dp_type = 'provide'
)
    AND pkgset_name = %(branch)s
    AND dp_type = 'require'
    AND pkg_sourcepackage IN %(sfilter)s
"""

    insert_result_for_depth_level = """
INSERT INTO {tmp_table} (pkgname)
SELECT DISTINCT *
FROM
(
    SELECT pkg_name
    FROM Packages_buffer
    WHERE pkg_filename IN
    (
        SELECT DISTINCT if(pkg_sourcepackage = 1, pkg_filename, pkg_sourcerpm) AS sourcerpm
        FROM Packages_buffer
        WHERE pkg_hash IN
        (
            {wrapper}
        )
    )
        AND pkg_sourcepackage = 1
    UNION ALL
    (
        SELECT * FROM {tmp_table}
    )
)
"""

    get_acl = """
SELECT DISTINCT
    acl_for,
    groupUniqArray(acl_list)
FROM last_acl
WHERE acl_for IN
(
    SELECT pkgname FROM {tmp_table}
)
    AND acl_branch = %(branch)s
GROUP BY acl_for
"""

    insert_src_deps = """
INSERT INTO {tmp_deps} (pkgname,reqname)
SELECT DISTINCT
    BinDeps.pkg_name,
    sourcepkgname
FROM
(
    SELECT DISTINCT
        BinDeps.pkg_name,
        pkg_name,
        sourcepkgname
   FROM last_packages_with_source
   INNER JOIN
    (
        SELECT DISTINCT 
            BinDeps.pkg_name,
            pkg_name
        FROM
        (
            SELECT DISTINCT
                BinDeps.pkg_name,
                pkg_name,
                dp_name
            FROM last_depends
            INNER JOIN
            (
                SELECT DISTINCT
                    pkg_name,
                    dp_name
                FROM last_depends
                WHERE pkg_name IN
                (
                    SELECT ''
                    UNION ALL
                        SELECT * FROM {tmp_table}
                )
                    AND pkgset_name = %(branch)s
                    AND dp_type = 'require'
                    AND pkg_sourcepackage = 1
            ) AS BinDeps USING dp_name
            WHERE pkgset_name = %(branch)s
                AND dp_type = 'provide'
                AND pkg_sourcepackage = 0
                AND pkg_arch IN ('x86_64', 'noarch')
        )
    ) AS pkgs USING pkg_name
WHERE pkgset_name = %(branch)s
ORDER BY sourcepkgname ASC
UNION ALL SELECT
    arrayJoin(%(pkgs)s),
    '',
    ''
)
"""

    insert_binary_deps = """
INSERT INTO {tmp_req} (pkgname, reqname)
SELECT
    sourcepkgname,
    Bin.sourcepkgname
FROM
(
    SELECT
        sourcepkgname,
        pkg_name AS pkgname,
        Bin.sourcepkgname
    FROM last_packages_with_source
    INNER JOIN
    (
        SELECT
            pkg_name,
            sourcepkgname
        FROM
        (
            SELECT DISTINCT
                pkg_name,
                Prv.pkg_name AS dp_name,
                Src.sourcepkgname
            FROM
            (
                SELECT
                    pkg_name,
                    dp_name,
                    Prv.pkg_name
                FROM
                (
                    SELECT DISTINCT
                        pkg_name,
                        dp_name
                    FROM last_depends
                    WHERE pkg_name IN
                    (
                        SELECT DISTINCT pkg_name
                        FROM last_packages_with_source
                        WHERE sourcepkgname IN
                        (
                            SELECT * FROM {tmp_table}
                        )
                            AND pkgset_name = %(branch)s
                            AND pkg_arch IN %(archs)s
                            AND pkg_name NOT LIKE '%%-debuginfo'
                    )
                        AND dp_type = 'require'
                        AND pkgset_name = %(branch)s
                        AND pkg_arch IN %(archs)s
                        AND pkg_sourcepackage = 0
                ) AS BinPkgDeps
                INNER JOIN
                (
                    SELECT
                        dp_name,
                        pkg_name
                    FROM last_depends
                    WHERE dp_type = 'provide'
                        AND pkgset_name = %(branch)s
                        AND pkg_sourcepackage = 0
                        AND pkg_arch IN %(archs)s
                ) AS Prv USING dp_name
            ) AS BinPkgProvDeps
            INNER JOIN
            (
                SELECT
                    pkg_name AS dp_name,
                    sourcepkgname
                FROM last_packages_with_source
                WHERE pkgset_name = %(branch)s
                    AND pkg_arch IN %(archs)s
            ) Src USING dp_name
        )
    ) AS Bin USING pkg_name
WHERE pkgset_name = %(branch)s
    AND pkg_arch IN %(archs)s)
"""

    get_all_filtred_pkgs_with_deps = """
SELECT DISTINCT
    pkgname,
    arrayFilter(x -> (x != pkgname AND notEmpty(x)), groupUniqArray(reqname)) AS arr
FROM package_dependency
WHERE reqname IN
(
    SELECT ''
    UNION ALL
        SELECT pkgname
        FROM package_dependency
)
GROUP BY pkgname
ORDER BY arr
"""

    select_finite_pkgs = """
SELECT pkgname
FROM {tmp_table}
WHERE pkgname NOT IN %(pkgs)s
"""

    get_output_data = """
SELECT DISTINCT 
    SrcPkg.pkg_name,
    SrcPkg.pkg_version,
    SrcPkg.pkg_release,
    SrcPkg.pkg_epoch,
    SrcPkg.pkg_serial_,
    pkg_sourcerpm AS filename,
    pkgset_name,
    groupUniqArray(pkg_arch),
    CAST(toDateTime(any(SrcPkg.pkg_buildtime)), 'String') AS buildtime_str
FROM last_packages
INNER JOIN
(
    SELECT
        pkg_name,
        pkg_version,
        pkg_release,
        pkg_epoch,
        pkg_serial_,
        pkg_filename as filename,
        pkgset_name,
        pkg_buildtime
    FROM last_packages
    WHERE pkg_name IN
    (
        SELECT * FROM {tmp_table}
    )
        AND pkgset_name = %(branch)s
        AND pkg_sourcepackage = 1
) AS SrcPkg USING filename
WHERE pkgset_name = %(branch)s
    AND pkg_sourcepackage = 0
GROUP BY
(
    SrcPkg.pkg_name,
    SrcPkg.pkg_version,
    SrcPkg.pkg_release,
    SrcPkg.pkg_epoch,
    SrcPkg.pkg_serial_,
    filename,
    pkgset_name
)
"""

    req_filter_by_src = """
SELECT DISTINCT pkg_name
FROM last_packages_with_source
WHERE sourcepkgname = %(srcpkg)s
    AND pkgset_name = %(branch)s
    AND pkg_arch IN ('x86_64','noarch')
    AND pkg_name NOT LIKE '%%debuginfo'
"""

    req_filter_by_binary = """
SELECT DISTINCT pkg_name
FROM last_depends
WHERE dp_name IN
(
    SELECT dp_name
    FROM last_depends
    WHERE pkg_name = '{pkg}'
        AND dp_type = 'provide'
        AND pkgset_name = %(branch)s
        AND pkg_sourcepackage = 0
        AND pkg_arch IN %(archs)s
)
    AND dp_type = 'require'
    AND pkgset_name = %(branch)s
    AND pkg_sourcepackage IN (0,1)
    AND pkg_name IN
    (
        SELECT DISTINCT pkg_name
        FROM
        (
            SELECT DISTINCT pkg_name
            FROM last_packages_with_source
            WHERE sourcepkgname IN
            (
                SELECT * FROM {tmp_table}
            )
                AND pkgset_name = %(branch)s
                AND pkg_sourcepackage = 0
                AND pkg_arch IN %(archs)s
                AND pkg_name NOT LIKE '%%-debuginfo'
        UNION ALL
            SELECT pkg_name
            FROM Packages_buffer
            WHERE pkg_name IN
            (
                SELECT * FROM {tmp_table}
            )
        )
    )
"""

    get_filter_pkgs = """
SELECT DISTINCT sourcepkgname
FROM last_packages_with_source
WHERE pkg_name IN
(
    SELECT DISTINCT *
    FROM ({base_query})
)
    AND pkgset_name = %(branch)s
    AND pkg_arch IN %(archs)s
"""

    misconflict_get_hshs_by_pkgs = """
SELECT
    pkg_hash,
    pkg_name
FROM last_packages
WHERE pkg_name IN %(pkgs)s
  AND pkgset_name = %(branch)s
  AND pkg_sourcepackage = 0
  AND pkg_arch IN %(arch)s
"""

    misconflict_get_pkgs_with_conflict = """
SELECT *
FROM
(
    SELECT
        InPkg.pkg_hash,
        pkg_hash,
        files,
        foundpkgname
    FROM
    (
        SELECT
            InPkg.pkg_hash,
            pkg_hash,
            groupUniqArray(file_hashname) AS files
        FROM
        (
            SELECT
                pkg_hash,
                file_hashname
            FROM Files_buffer
            PREWHERE file_hashname IN
            (
                SELECT file_hashname
                FROM Files_buffer
                WHERE pkg_hash IN %(hshs)s AND file_class != 'directory'
            )
                AND pkg_hash IN
                (
                    SELECT pkg_hash
                    FROM last_packages
                    WHERE pkg_hash NOT IN %(hshs)s
                        AND pkgset_name= %(branch)s
                        AND pkg_sourcepackage = 0
                        AND pkg_name NOT LIKE '%%-debuginfo'
                        AND pkg_arch IN %(arch)s
                )
            ) AS LeftPkg
            LEFT JOIN
            (
                SELECT
                    pkg_hash,
                    file_hashname
                FROM Files_buffer
                WHERE pkg_hash IN %(hshs)s AND file_class != 'directory'
            ) AS InPkg USING file_hashname
        GROUP BY (InPkg.pkg_hash, pkg_hash)
    ) AS Sel1
    LEFT JOIN
    (
        SELECT
            pkg_name AS foundpkgname,
            pkg_hash
        FROM last_packages
        WHERE pkgset_name = %(branch)s AND pkg_sourcepackage = 0
    ) AS pkgCom ON Sel1.pkg_hash = pkgCom.pkg_hash
) AS Sel2
LEFT JOIN
(
    SELECT
        pkg_name AS inpkgname,
        pkg_hash
    FROM last_packages
    WHERE pkgset_name = %(branch)s AND pkg_sourcepackage = 0
) AS pkgIn ON pkgIn.pkg_hash = InPkg.pkg_hash
WHERE foundpkgname != inpkgname
"""

    misconflict_get_fnames_by_fnhashs = """
SELECT fn_hash,
       fn_name
FROM FileNames_buffer
WHERE fn_hash IN %(hshs)s
"""

    misconflict_get_pkg_archs = """
SELECT
    pkg_name,
    groupUniqArray(pkg_arch)
FROM Packages_buffer
WHERE pkg_hash IN {hshs}
GROUP BY pkg_name
"""

    misconflict_get_meta_by_hshs = """
SELECT 
    pkg_name,
    pkg_version,
    pkg_release,
    pkg_epoch,
    groupUniqArray(pkg_arch)
FROM last_packages
WHERE pkg_name IN %(pkgs)s
    AND pkgset_name = %(branch)s
    AND pkg_sourcepackage = 0
    AND pkg_arch IN %(arch)s
GROUP BY 
(
    pkg_name,
    pkg_version,
    pkg_release,
    pkg_epoch
)
"""

    pkg_info_get_changelog = """
SELECT
    pkg_hash,
    changelog
FROM PackageChangelog_view
WHERE pkg_hash IN %(pkghshs)s
"""

    pkg_info_get_pkgs_template = """
SELECT DISTINCT
    pkg_hash,
    {p_params}
FROM last_packages
WHERE {p_values} {branch}
"""

    pkg_info_get_files = """
SELECT
    pkg_hash,
    groupUniqArray(file_name)
FROM Files_view
WHERE pkg_hash IN %(pkghshs)s
GROUP BY pkg_hash
"""

    pkg_info_get_depends = """
SELECT DISTINCT
    pkg_hash,
    dp_type,
    dp_name
FROM last_depends
WHERE pkg_hash IN %(pkghshs)s
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
GROUP BY
    pkgset_name,
    sourcepkgname,
    pkg_version,
    pkg_release
ORDER BY pkgset_date DESC
"""


packagesql = SQL()
