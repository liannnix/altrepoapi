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

    select_all_tmp_table = """
SELECT * FROM {tmp_table}
"""

    insert_into_tmp_table = """
INSERT INTO {tmp_table} (*) VALUES
"""

    drop_tmp_table = """
DROP TABLE {tmp_table}
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
    FROM SrcPackagesLastChangelog
    ) AS CHLG ON CHLG.pkg_hash = last_packages.pkg_hash
WHERE pkgset_name = %(branch)s
    AND pkg_sourcepackage IN {src}
    AND pkg_buildtime >= %(buildtime)s
    AND pkg_name NOT LIKE '%%-debuginfo'
    {group}
ORDER BY pkg_name
"""

    get_group_subgroups = """
SELECT DISTINCT pkg_group_
FROM last_packages
WHERE pkgset_name = %(branch)s
    AND pkg_sourcepackage IN {src}
    AND pkg_name NOT LIKE '%%-debuginfo'
    AND pkg_group_ like '{group}/%%'
    AND pkg_group_ != '{group}'
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
    WHERE {name_like}
        AND pkg_sourcepackage = 1
        {branch}
),
lp_preselect2 AS
(
    SELECT
        pkg_hash,
        pkgset_name
    FROM static_last_packages
    WHERE NOT ({name_like})
        AND pkg_sourcepackage = 1
        {branch}
)
SELECT
    pkg_name,
    groupUniqArray((LP.pkgset_name, pkg_version, pkg_release, toString(pkg_hash))),
    max(pkg_buildtime),
    argMax(pkg_url, pkg_buildtime),
    argMax(pkg_summary, pkg_buildtime),
    any(pkg_group_),
    1 AS is_source
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
    any(pkg_group_),
    0 AS is_source
FROM Packages
INNER JOIN lp_preselect2 AS LP2 USING (pkg_hash)
WHERE NOT ({name_like})
    AND pkg_sourcepackage = 1
    AND pkg_sourcerpm IN
    (
        SELECT pkg_sourcerpm
        FROM Packages
        WHERE pkg_sourcepackage = 0
            AND {name_like}
            {arch}
    )
    {branch}
GROUP BY pkg_name
ORDER BY pkg_name
"""

    get_find_packages_by_name_and_arch = """
WITH
lp_preselect AS
(
    SELECT
        pkg_hash,
        pkgset_name
    FROM static_last_packages
    WHERE {name_like}
        AND pkg_sourcepackage = 1
        {branch}
),
srcs_by_arch AS
(
    SELECT
        pkg_hash,
        pkgset_name
    FROM lp_preselect
    WHERE pkg_hash IN (
        SELECT pkg_srcrpm_hash
        FROM Packages
        WHERE pkg_sourcepackage = 0
            AND pkg_srcrpm_hash IN (
                SELECT pkg_hash FROm lp_preselect
            )
            {arch}
    )
),
lp_preselect2 AS
(
    SELECT
        pkg_hash,
        pkgset_name
    FROM static_last_packages
    WHERE NOT {name_like}
        AND pkg_sourcepackage = 1
        {branch}
)
SELECT
    pkg_name,
    groupUniqArray((LP.pkgset_name, pkg_version, pkg_release, toString(pkg_hash))),
    max(pkg_buildtime),
    argMax(pkg_url, pkg_buildtime),
    argMax(pkg_summary, pkg_buildtime),
    any(pkg_group_),
    1 AS is_source
FROM Packages
INNER JOIN srcs_by_arch AS LP USING (pkg_hash)
WHERE pkg_hash IN
(
    SELECT pkg_hash FROM srcs_by_arch
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
    any(pkg_group_),
    0 AS is_source
FROM Packages
INNER JOIN lp_preselect2 AS LP2 USING (pkg_hash)
WHERE NOT {name_like}
    AND pkg_sourcepackage = 1
    AND pkg_sourcerpm IN
    (
        SELECT pkg_sourcerpm
        FROM Packages
        WHERE pkg_sourcepackage = 0
            AND {name_like}
            {arch}
            AND pkg_hash IN (
                SELECT pkg_hash
                FROM static_last_packages
                WHERE pkg_sourcepackage = 0
                    {branch}
            )
    )
    {branch}
GROUP BY pkg_name
ORDER BY pkg_name
"""

    get_find_deleted_packages_by_name = """
WITH
deleted_src_pkgs AS (
    SELECT pkgset_name, pkg_name, hash
    FROM lv_branch_deleted_packages
    WHERE {name_like}
    {branch}
)
SELECT
    pkg_name,
    groupUniqArray((pkgset_name, pkg_version, pkg_release, toString(pkg_hash))),
    max(pkg_buildtime),
    any(pkg_url),
    any(pkg_summary),
    any(pkg_group_)
FROM (
    SELECT *
    FROM deleted_src_pkgs
    LEFT JOIN (
        SELECT
            pkg_hash,
            pkg_buildtime,
            pkg_version,
            pkg_release,
            pkg_summary,
            pkg_url,
            pkg_group_
        FROM Packages
        WHERE pkg_sourcepackage = 1
            AND pkg_hash IN (SELECT hash FROM deleted_src_pkgs)
    ) AS PI ON PI.pkg_hash = hash
)
GROUP BY pkg_name
ORDER BY pkg_name
"""

    get_fast_search_packages_by_name = """
SELECT DISTINCT
    pkg_name,
    pkg_sourcepackage,
    groupUniqArray(pkgset_name)
FROM static_last_packages
WHERE {name_like}
    AND pkg_name NOT LIKE '%-debuginfo'
    {branch}
GROUP BY
    pkg_name,
    pkg_sourcepackage
ORDER BY
    pkg_sourcepackage DESC,
    pkg_name
"""

    get_fast_search_deleted_packages_by_name = """
SELECT DISTINCT
    pkg_name,
    1,
    groupUniqArray(pkgset_name)
FROM lv_branch_deleted_packages
WHERE {name_like}
{branch}
GROUP BY pkg_name
ORDER BY pkg_name
"""

    get_last_branch_date = """
SELECT DISTINCT pkgset_date
FROM lv_pkgset_stat
WHERE pkgset_name = '{branch}'
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

    get_last_branch_src_diff = """
CREATE TEMPORARY TABLE {tmp_table} AS
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
                        AND pkgset_date < '{last_pkgset_date}'
                )
        )
    )
"""

    check_tmp_table_count = """
SELECT count() FROM {tmp_table}
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
        FROM SrcPackagesLastChangelog
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

    get_pkghash_by_BVR = """
SELECT max(pkg_hash)
FROM PackageSet
WHERE pkgset_uuid IN (
    SELECT pkgset_uuid
    FROM PackageSetName
    WHERE pkgset_depth = 1 AND pkgset_nodename = 'srpm'
        AND pkgset_ruuid IN (
            SELECT pkgset_uuid
            FROM PackageSetName
            WHERE pkgset_depth = 0
                AND pkgset_nodename = '{branch}'
        )
) AND pkg_hash IN (
    SELECT pkg_hash
    FROM Packages
    WHERE pkg_name = '{name}'
        AND pkg_sourcepackage = 1
        AND pkg_version = '{version}'
        AND pkg_release = '{release}'
)
"""

    get_source_pkg_name = """
SELECT DISTINCT
    pkg_name
FROM Packages
WHERE pkg_hash IN (
    SELECT pkg_srcrpm_hash
    FROM Packages
    WHERE pkg_hash IN (
        SELECT pkg_hash
        FROM static_last_packages
        WHERE pkg_name = '{name}'
            AND pkgset_name = '{branch}'
        )
)
"""

    get_src_pkg_by_bin = """
SELECT DISTINCT
    pkg_name
FROM BranchPackageHistory
WHERE pkg_hash IN (
    SELECT pkg_srcrpm_hash
    FROM Packages
    WHERE pkg_name = '{name}'
        AND pkg_sourcepackage = 0
    ORDER BY pkg_srcrpm_hash ASC
) AND pkg_sourcepackage = 1
  AND pkgset_name = '{branch}'
ORDER BY task_changed DESC LIMIT 1
"""


sql = SQL()
