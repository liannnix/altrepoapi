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
    create_tmp_table = """
CREATE TEMPORARY TABLE {tmp_table} {columns}
"""

    insert_into_tmp_table = """
INSERT INTO {tmp_table} (*) VALUES
"""

    select_all_tmp_table = """
SELECT * FROM {tmp_table}
"""

    truncate_tmp_table = """
TRUNCATE TABLE {tmp_table}
"""

    drop_tmp_table = """
DROP TABLE {tmp_table}
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

    get_depends_bin_pkg = """
SELECT
    dp_name,
    dp_version,
    dp_flag,
    dp_type
FROM Depends
WHERE pkg_hash = {pkghash}
"""

    make_src_depends_tmp = """
CREATE TEMPORARY TABLE {tmp_table} AS
SELECT
    dp_name,
    dp_version,
    dp_flag
FROM Depends
WHERE pkg_hash = {pkghash}
    AND dp_type = 'require'
"""

    make_src_by_bin_deps_tmp = """
CREATE TEMPORARY TABLE {tmp_table_2} AS
SELECT DISTINCT
    pkg_hash
FROM static_last_packages
WHERE pkg_sourcepackage = 1
    AND pkgset_name = '{branch}'
    AND pkg_hash IN
    (
        SELECT pkg_srcrpm_hash
        FROM Packages
        WHERE pkg_hash IN
        (
            SELECT pkg_hash
            FROM Depends
            WHERE dp_type = 'provide'
                AND dp_name IN
                (SELECT dp_name FROM {tmp_table})
        )
    )
"""

    get_src_by_bin_deps = """
SELECT DISTINCT
    pkg_hash,
    pkg_name,
    pkg_version,
    pkg_release,
    pkg_summary
FROM Packages
WHERE pkg_sourcepackage = 1
    AND pkg_hash IN
        (SELECT pkg_hash FROM {tmp_table})
"""

    get_pkgs_name_and_arch = """
SELECT
    pkg_name,
    pkg_arch
FROM Packages
WHERE pkg_hash = {pkghash}
"""

    get_pkg_info = """
SELECT
    pkg_name,
    pkg_epoch,
    pkg_version,
    pkg_release,
    pkg_buildtime
FROM Packages
WHERE pkg_hash = {pkghash}
"""

    get_pkgs_depends = """
SELECT toString(pkg_hash), dp_type
FROM last_depends
WHERE dp_name = '{dp_name}'
    AND pkgset_name = '{branch}'
    {dp_type}
"""

    get_repo_packages = """
SELECT DISTINCT
    toString(pkg_hash),
    pkg_name,
    pkg_version,
    pkg_release,
    pkg_arch,
    pkg_sourcepackage,
    pkg_buildtime,
    pkg_summary,
    pkg_packager_email,
    pkg_group_
FROM last_packages
WHERE pkgset_name = '{branch}'
    AND pkg_hash IN (SELECT * FROM {tmp_table})
    AND pkg_buildtime >= 0
ORDER BY pkg_name
"""

    get_pkgset_depends = """
SELECT
    count(pkg_hash),
    pkgset_name
FROM last_depends
WHERE dp_name = '{dp_name}'
    {dp_type}
group by pkgset_name
"""

    taskless_template = """
AS
SELECT * FROM Depends
WHERE pkg_hash IN (
    SELECT pkg_hash
    FROM static_last_packages
    WHERE pkgset_name = '{branch}'
)
"""

    task_template = """
AS
SELECT * FROM Depends
WHERE pkg_hash IN (
    SELECT pkg_hash
    FROM {ext_table}
)
"""

    get_dependencies = """
SELECT
    pkg_sourcerpm,
    pkg_name,
    pkg_epoch,
    pkg_version,
    pkg_release,
    if(pkg_sourcepackage, 'src', pkg_arch) AS pkg_arch,
    dp_type,
    dp_name,
    dp_flag,
    dp_version
FROM Packages
INNER JOIN
(
    WITH hashes AS
        (
            SELECT pkg_hash
            FROM {branch_deps_table_name}
            WHERE (dp_name IN (SELECT name FROM {tmp_table}))
                AND (dp_type = 'provide')
        )
    SELECT DISTINCT
        pkg_hash,
        dp_type,
        dp_name,
        dp_flag,
        dp_version
    FROM {branch_deps_table_name}
    WHERE (pkg_hash IN (
        SELECT pkg_hash
        FROM hashes
        UNION ALL
        SELECT pkg_srcrpm_hash
        FROM Packages
        WHERE pkg_hash IN hashes
    )) AND dp_type = '{dptype}'
) AS H USING (pkg_hash)
WHERE (pkg_arch IN {archs})
"""

    get_what_depends_src = """
WITH
(
    SELECT DISTINCT pkg_hash
    FROM static_last_packages
    WHERE pkgset_name = '{branch}'
        AND pkg_name = '{pkg_name}'
        AND pkg_sourcepackage = 1
) AS in_src_pkg_hash,
in_bin_pkgs AS (
    SELECT DISTINCT
        pkg_hash,
        pkg_name,
        pkg_arch
    FROM Packages
    WHERE pkg_sourcepackage = 0
        AND pkg_srcrpm_hash = in_src_pkg_hash
        AND pkg_hash IN (
            SELECT pkg_hash
            FROM static_last_packages
            WHERE pkgset_name = '{branch}'
                AND pkg_sourcepackage = 0
        )
        AND pkg_arch in {archs}
        AND pkg_name NOT LIKE '%%-debuginfo'
),
in_bin_pkgs_provides AS (
    SELECT
        pkg_hash AS in_bin_pkg_hash,
        pkg_name AS in_bin_pkg_name,
        pkg_arch AS in_bin_pkg_arch,
        dp_name AS in_bin_dp_name,
        dp_version AS in_bin_dp_version,
        dp_flag AS in_bin_dp_flag
    FROM Depends
    LEFT JOIN in_bin_pkgs AS IPB USING pkg_hash
    WHERE dp_type = 'provide'
        AND pkg_hash IN (SELECT pkg_hash FROM in_bin_pkgs)
    AND pkg_name NOT LIKE '%%-debuginfo'
),
repo_other_pkgs_hshs AS (
    SELECT pkg_hash
    FROM static_last_packages
    WHERE pkgset_name = '{branch}'
        AND pkg_hash NOT IN (SELECT pkg_hash FROM in_bin_pkgs)
)
SELECT
    ROP.pkg_srcrpm_hash AS src_hash,
    ROP.pkg_srcrpm_name AS src_name,
    ROP.buildtime AS src_buildtime,
    'sisyphus' AS branch,
    groupUniqArray((
        ROP.pkg_hash AS pkg_hash,
        ROP.pkg_name AS pkg_name,
        ROP.arch AS arch,
        dp_name,
        dp_version,
        dp_flag,
        IBPP.*
    ))
FROM Depends
INNER JOIN (
    SELECT DISTINCT
            pkg_srcrpm_hash,
            TT.pkg_name AS pkg_srcrpm_name,
            TT.buildtime_str AS buildtime,
            pkg_hash,
            pkg_name,
            if(pkg_sourcepackage = 0, pkg_arch, 'srpm') AS arch
        FROM Packages
        LEFT JOIN (
            SELECT pkg_hash,
                   pkg_name,
                   CAST(toDateTime(any(pkg_buildtime)), 'String') AS buildtime_str
            FROM Packages
                WHERE pkg_hash IN (
                    SELECT pkg_hash
                    FROM static_last_packages
                    WHERE pkgset_name = '{branch}'
                    AND pkg_sourcepackage = 1
                )
            AND pkg_sourcepackage = 1
            GROUP BY pkg_hash, pkg_name
    ) AS TT ON TT.pkg_hash = Packages.pkg_srcrpm_hash
    WHERE pkg_sourcepackage IN {sfilter}
     AND pkg_hash IN repo_other_pkgs_hshs
     AND arch in {src_archs}
) AS ROP USING pkg_hash
LEFT JOIN in_bin_pkgs_provides AS IBPP ON
    (in_bin_dp_name = dp_name AND in_bin_pkg_arch = arch)
    OR (in_bin_dp_name = dp_name AND arch = 'noarch' AND in_bin_pkg_arch = 'x86_64')
    OR (in_bin_dp_name = dp_name AND arch = 'srpm' AND in_bin_pkg_arch IN {archs})
WHERE dp_type = 'require'
    AND dp_name IN (SELECT DISTINCT in_bin_dp_name FROM in_bin_pkgs_provides)
GROUP BY src_hash, src_name, src_buildtime
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
    AND acl_branch = '{branch}'
GROUP BY acl_for
"""


sql = SQL()
