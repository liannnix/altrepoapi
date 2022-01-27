# ALTRepo API
# Copyright (C) 2021  BaseALT Ltd

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

    truncate_tmp_table = """
TRUNCATE TABLE {tmp_table}
"""

    insert_into_tmp_table = """
INSERT INTO {tmp_table} (*) VALUES
"""

    drop_tmp_table = """
DROP TABLE {tmp_table}
"""

    insert_last_packages_hashes = """
INSERT INTO {tmp_table}
SELECT pkg_hash
FROM static_last_packages
WHERE pkgset_name = '{branch}'
"""

    insert_pkgs_hshs_filtered_src = """
INSERT INTO {tmp_table}
SELECT pkg_hash
FROM Packages
WHERE pkg_hash IN
(
    SELECT pkg_hash FROM {tmp_table2}
)
    AND pkg_sourcepackage = 1
"""

    insert_pkgs_hshs_filtered_bin = """
INSERT INTO {tmp_table}
SELECT pkg_hash
FROM Packages
WHERE pkg_hash IN
(
    SELECT pkg_hash FROM {tmp_table2}
)
    AND pkg_sourcepackage = 0
    AND pkg_name NOT LIKE '%%-debuginfo'
    AND pkg_arch in {arch}
"""

    create_shadow_last_pkgs_w_srcs = """
CREATE TEMPORARY TABLE last_packages_with_source
(pkg_hash UInt64, pkg_name String, pkg_arch String, sourcepkgname String, pkgset_name String)
"""

    fill_shadow_last_pkgs_w_srcs = """
INSERT INTO last_packages_with_source SELECT
    pkg_hash,
    pkg_name,
    pkg_arch,
    sourcepkgname,
    '{branch}' AS pkgset_name
FROM
(
    SELECT
        pkg_hash,
        pkg_name,
        pkg_arch,
        srcPackage.pkg_name AS sourcepkgname,
        pkg_srcrpm_hash
    FROM Packages
    LEFT JOIN
    (
        SELECT
            pkg_hash AS pkg_srcrpm_hash,
            pkg_name
        FROM Packages
        WHERE pkg_sourcepackage = 1
    ) AS srcPackage USING (pkg_srcrpm_hash)
    WHERE pkg_sourcepackage = 0
        AND pkg_srcrpm_hash != 0
        AND pkg_hash IN
        (
            SELECT pkg_hash FROM {tmp_table}
        )
)
"""

    create_shadow_last_dependss = """
CREATE TEMPORARY TABLE last_depends
(pkg_hash UInt64, dp_name String, dp_type String, pkg_name String, pkg_arch String, pkg_sourcepackage UInt8, pkgset_name String)
"""

    fill_shadow_last_depends = """
INSERT INTO last_depends
SELECT
    pkg_hash,
    dp_name,
    dp_type,
    pkg_name,
    pkg_arch,
    pkg_sourcepackage,
    '{branch}' AS pkgset_name
FROM Depends
INNER JOIN
(
    SELECT
        pkg_hash,
        pkg_name,
        pkg_sourcepackage,
        pkg_arch
    FROM Packages
) AS PkgSet USING (pkg_hash)
WHERE pkg_hash IN
(
    SELECT pkg_hash FROM {tmp_table}
)
"""

    insert_build_req_deep_1 = """
INSERT INTO {tmp_table}
SELECT DISTINCT pkg_name
FROM Packages
WHERE 
(
    pkg_filename IN
    (
        SELECT DISTINCT if(pkg_sourcepackage = 1, pkg_filename, pkg_sourcerpm) AS sourcerpm
        FROM Packages
        WHERE pkg_hash IN
        (
            SELECT DISTINCT pkg_hash
            FROM last_depends
            WHERE dp_name IN
            (
                SELECT dp_name
                FROM Depends
                WHERE pkg_hash IN
                (
                    SELECT pkg_hash
                    FROM last_packages_with_source
                    WHERE sourcepkgname IN %(pkgs)s
                        AND pkgset_name = %(branch)s
                        AND pkg_arch IN %(archs)s
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
            AND pkg_arch IN %(archs)s
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
    FROM Packages
    WHERE pkg_filename IN
    (
        SELECT DISTINCT if(pkg_sourcepackage = 1, pkg_filename, pkg_sourcerpm) AS sourcerpm
        FROM Packages
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

    filter_l2_src_pkgs = """
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
                    SELECT * FROM {tmp_table1}
                )
                    AND pkgset_name = %(branch)s
                    AND dp_type = 'require'
                    AND pkg_sourcepackage = 1
            ) AS BinDeps USING dp_name
            WHERE pkgset_name = %(branch)s
                AND dp_type = 'provide'
                AND pkg_sourcepackage = 0
                AND pkg_arch IN %(archs)s
        )
    ) AS pkgs USING pkg_name
WHERE pkgset_name = %(branch)s
)
WHERE sourcepkgname IN
(
    SELECT * FROM {tmp_table2}
)
"""

    insert_src_deps = (
# get source packages that provides dependencies required by input list
# 'BinDeps.pkg_name' - input source package
# 'sourcepkgname' - source packages that provides binary packages required by 'BinDeps.pkg_name'
"""
INSERT INTO {tmp_deps} (pkgname,reqname)
SELECT DISTINCT
    BinDeps.pkg_name,
    sourcepkgname
FROM
("""
# get 'sourcepkgname' by 'pkg_name'
"""
    SELECT DISTINCT
        BinDeps.pkg_name,
        pkg_name,
        sourcepkgname
    FROM
    (
        SELECT DISTINCT 
            pkg_name AS `BinDeps.pkg_name`,
            SrcDeps.pkg_name AS pkg_name_
        FROM
        ("""
# get binary packages ('SrcDeps.pkg_name') required in 'dp_name' by 'pkg_name'
"""
            SELECT DISTINCT
                SrcDeps.pkg_name,
                pkg_name,
                dp_name
            FROM last_depends
            INNER JOIN
            (
                SELECT DISTINCT
                    pkg_name,
                    dp_name
                FROM last_depends
                WHERE pkgset_name = %(branch)s
                    AND dp_type = 'provide'
                    AND pkg_sourcepackage = 0
                    AND pkg_arch IN %(archs)s
            ) AS SrcDeps USING dp_name
            WHERE pkg_name IN
            (
                SELECT ''
                UNION ALL
                    SELECT * FROM {tmp_table}
            )
                AND pkgset_name = %(branch)s
                AND dp_type = 'require'
                AND pkg_sourcepackage = 1
        )
    ) AS pkgs
    INNER JOIN
    (
        SELECT pkg_name, sourcepkgname
        FROM last_packages_with_source
        WHERE pkgset_name = %(branch)s
    ) AS LPWS ON (LPWS.pkg_name = pkg_name_)
UNION ALL SELECT
    arrayJoin(%(pkgs)s),
    '',
    ''
)
"""
    )

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
UNION ALL SELECT
    arrayJoin(%(pkgs)s),
    ''
"""

    get_all_filtred_pkgs_with_deps = """
SELECT DISTINCT
    pkgname,
    arrayFilter(x -> (x != pkgname AND notEmpty(x)), groupUniqArray(reqname)) AS arr
FROM {tmp_table}
WHERE reqname IN
(
    SELECT ''
    UNION ALL
        SELECT pkgname
        FROM {tmp_table}
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
    '{branch}' AS pkgset_name,
    groupUniqArray(pkg_arch),
    CAST(toDateTime(any(SrcPkg.pkg_buildtime)), 'String') AS buildtime_str
FROM Packages
INNER JOIN
(
    SELECT
        pkg_name,
        pkg_version,
        pkg_release,
        pkg_epoch,
        pkg_serial_,
        pkg_filename as filename,
        pkg_buildtime
    FROM Packages
    WHERE pkg_name IN
    (
        SELECT * FROM {tmp_table}
    )
        AND pkg_hash IN
        (
            SELECT pkg_hash FROM {tmp_table2}
        )
        AND pkg_sourcepackage = 1
) AS SrcPkg USING filename
WHERE pkg_sourcepackage = 0
    AND pkg_hash IN
    (
        SELECT pkg_hash FROM {tmp_table2}
    )
GROUP BY
(
    SrcPkg.pkg_name,
    SrcPkg.pkg_version,
    SrcPkg.pkg_release,
    SrcPkg.pkg_epoch,
    SrcPkg.pkg_serial_,
    filename
)
"""

    req_filter_by_src = """
SELECT DISTINCT pkg_name
FROM last_packages_with_source
WHERE sourcepkgname = %(srcpkg)s
    AND pkgset_name = %(branch)s
    AND pkg_arch IN %(archs)s
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
            FROM Packages
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
            FROM Files
            PREWHERE file_hashname IN
            (
                SELECT file_hashname
                FROM Files
                WHERE pkg_hash IN
                (
                    SELECT pkg_hash FROM {tmp_table2}
                )
                    AND file_class != 'directory'
            )
                AND pkg_hash IN
                (
                    SELECT pkg_hash
                    FROM Packages
                    WHERE pkg_hash NOT IN
                    (
                        SELECT pkg_hash FROM {tmp_table2}
                    )
                        AND pkg_hash IN
                        (
                            SELECT pkg_hash FROM {tmp_table}
                        )
                        AND pkg_sourcepackage = 0
                )
            ) AS LeftPkg
            LEFT JOIN
            (
                SELECT
                    pkg_hash,
                    file_hashname
                FROM Files
                WHERE pkg_hash IN
                (
                    SELECT pkg_hash FROM {tmp_table2}
                )
                    AND file_class != 'directory'
            ) AS InPkg USING file_hashname
        GROUP BY (InPkg.pkg_hash, pkg_hash)
    ) AS Sel1
    LEFT JOIN
    (
        SELECT
            pkg_name AS foundpkgname,
            pkg_hash
        FROM Packages
        WHERE pkg_sourcepackage = 0
    ) AS pkgCom ON Sel1.pkg_hash = pkgCom.pkg_hash
) AS Sel2
LEFT JOIN
(
    SELECT
        pkg_name AS inpkgname,
        pkg_hash
    FROM Packages
    WHERE pkg_sourcepackage = 0
) AS pkgIn ON pkgIn.pkg_hash = InPkg.pkg_hash
WHERE foundpkgname != inpkgname
"""

    misconflict_get_fnames_by_fnhashs = """
SELECT fn_hash,
       fn_name
FROM FileNames
WHERE fn_hash IN %(hshs)s
"""

    misconflict_get_pkg_archs = """
SELECT
    pkg_name,
    groupUniqArray(pkg_arch)
FROM Packages
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
FROM Packages
WHERE pkg_name IN {pkgs}
    AND pkg_hash IN
    (
        SELECT pkg_hash FROM {tmp_table}
    )
    AND pkg_sourcepackage = 0
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
    {branchs}
GROUP BY
    pkgset_name,
    sourcepkgname,
    pkg_version,
    pkg_release
ORDER BY pkgset_date DESC
"""

    gen_table_hshs_by_file = """
CREATE TEMPORARY TABLE {tmp_table} AS
SELECT DISTINCT
    pkg_hash,
    file_hashname
FROM Files
WHERE pkg_hash IN
(
    SELECT pkg_hash
    FROM last_packages
    WHERE pkgset_name = %(branch)s
        AND pkg_arch IN %(arch)s
)
    AND {param}
"""

    gen_table_hshs_by_file_mod_hashname = """
file_hashname IN
(
    SELECT fn_hash
    FROM {tmp_table}
)
"""

    gen_table_hshs_by_file_mod_md5 = """
file_md5 = unhex(%(elem)s)
"""

    gen_table_fnhshs_by_file = """
CREATE TEMPORARY TABLE {tmp_table} AS
SELECT fn_hash, fn_name
FROM FileNames
WHERE fn_name LIKE %(elem)s
"""

    pkg_by_file_get_meta_by_hshs = """
SELECT pkg_hash,
       lower(hex(pkg_cs)) AS pkg_cs,
       pkg_name,
       pkg_sourcepackage,
       pkg_version,
       pkg_release,
       pkg_disttag,
       pkg_arch,
       %(branch)s
FROM Packages
WHERE pkg_hash IN
(
    SELECT pkg_hash FROM {tmp_table}
)
"""

    pkg_by_file_get_fnames_by_fnhashs = """
SELECT fn_hash,
       fn_name
FROM FileNames
WHERE fn_hash IN
(
    SELECT file_hashname from {tmp_table}
)
"""

    get_dependent_packages = """
SELECT DISTINCT
    pkg_name,
    pkg_version,
    pkg_release,
    pkg_epoch,
    pkg_serial_,
    pkg_filename AS sourcerpm,
    pkgset_name,
    groupUniqArray(binary_arch)
FROM last_packages
INNER JOIN
(
    SELECT
        pkg_sourcerpm,
        pkg_arch AS binary_arch
    FROM last_packages
    WHERE pkg_name IN
    (
        SELECT DISTINCT pkg_name
        FROM last_depends
        WHERE dp_name IN
        (
            SELECT dp_name
            FROM last_depends
            WHERE pkg_name = '{package}'
                AND dp_type = 'provide'
                AND pkgset_name = '{branch}'
                AND pkg_sourcepackage = 0
        )
            AND pkgset_name = '{branch}'
            AND pkg_sourcepackage = 0
    )
        AND pkgset_name = '{branch}'
        AND pkg_sourcepackage = 0
) AS SrcPkg USING pkg_sourcerpm
WHERE pkgset_name = '{branch}'
    AND pkg_sourcepackage = 1
GROUP BY
(
    pkg_name,
    pkg_version,
    pkg_release,
    pkg_epoch,
    pkg_serial_,
    sourcerpm,
    pkgset_name
)
"""

    get_unpackaged_dirs = """
SELECT DISTINCT
    Pkg.pkg_name,
    extract(file_name, '^(.+)/([^/]+)$') AS dir,
    Pkg.pkg_version,
    Pkg.pkg_release,
    Pkg.pkg_epoch,
    Pkg.pkg_packager,
    Pkg.pkg_packager_email,
    groupUniqArray(Pkg.pkg_arch)
FROM Files_view
LEFT JOIN
(
    SELECT
        pkg_hash,
        pkg_name,
        pkg_version,
        pkg_release,
        pkg_epoch,
        pkg_disttag,
        pkg_packager_email,
        pkg_packager,
        pkg_arch
    FROM Packages
) AS Pkg USING pkg_hash
WHERE file_class = 'file'
    AND pkg_hash IN
    (
        SELECT pkg_hash
        FROM last_packages
        WHERE pkgset_name = %(branch)s
            AND pkg_packager_email LIKE %(email)s
            AND pkg_sourcepackage = 0
            AND pkg_arch IN %(archs)s
    )
    AND file_hashdir NOT IN
    (
        SELECT file_hashname
        FROM Files
        WHERE file_class = 'directory'
            AND pkg_hash IN
            (
                SELECT pkg_hash
                FROM last_packages
                WHERE pkgset_name = %(branch)s
                AND pkg_sourcepackage = 0
                AND pkg_arch IN %(archs)s
            )
    )
GROUP BY
(
    Pkg.pkg_name,
    dir,
    Pkg.pkg_version,
    Pkg.pkg_release,
    Pkg.pkg_epoch,
    Pkg.pkg_packager,
    Pkg.pkg_packager_email
)
ORDER BY pkg_packager_email
"""

    get_pkg_hshs = """
SELECT pkg_hash
FROM last_packages
WHERE pkg_name IN {pkgs}
    AND pkgset_name = '{branch}'
    AND pkg_sourcepackage = 1
"""

    insert_into_repocop = """
INSERT INTO PackagesRepocop (*) VALUES
"""

    get_out_repocop = """
SELECT
    pkg_name,
    pkg_version,
    pkg_release,
    pkg_arch,
    pkgset_name,
    rc_test_name,
    argMax(rc_test_status, rc_test_date),
    argMax(rc_test_message, rc_test_date),
    max(rc_test_date)
FROM PackagesRepocop
WHERE pkgset_name = '{branch}'
    {pkgs}
    {srcpkg_version}
    {srcpkg_release}
    {arch}
GROUP BY
    pkg_name,
    pkg_version,
    pkg_release,
    pkg_arch,
    pkgset_name,
    rc_test_name
ORDER BY
    pkg_name ASC,
    pkg_arch ASC
"""

    get_specfile_by_hash = """
SELECT
    pkg_hash,
    pkg_name,
    pkg_version,
    pkg_release,
    specfile_name,
    specfile_date,
    base64Encode(specfile_content),
    length(specfile_content)
FROM Specfiles
WHERE pkg_hash = {pkghash}
"""

    get_specfile_by_name = """
SELECT
    pkg_hash,
    pkg_name,
    pkg_version,
    pkg_release,
    specfile_name,
    specfile_date,
    base64Encode(specfile_content),
    length(specfile_content)
FROM Specfiles
WHERE pkg_hash IN
(
    SELECT pkg_hash
    FROM static_last_packages
    WHERE pkg_sourcepackage = 1
        AND pkgset_name = '{branch}'
        AND pkg_name = '{name}'
)
"""

    get_pkg_files = """
WITH
pkg_files AS
(
    SELECT DISTINCT
        file_hashname,
        file_size,
        file_class,
        file_linkto,
        file_mtime,
        file_mode
    FROM Files
    WHERE pkg_hash = {pkghash}
)
SELECT
    FN.fn_name as filename,
    PF.file_size,
    PF.file_class,
    PF.file_linkto,
    PF.file_mtime,
    PF.file_mode
FROM
(SELECT * FROM pkg_files) AS PF
LEFT JOIN
(
    SELECT DISTINCT
        fn_hash,
        fn_name
    FROM FileNames
    WHERE fn_hash IN
    (SELECT file_hashname FROM pkg_files)
) AS FN ON FN.fn_hash = PF.file_hashname
ORDER BY filename
"""


sql = SQL()
