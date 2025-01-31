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
    get_repo_packages = """
SELECT
    pkg_hash,
    pkg_name,
    pkg_version,
    pkg_release,
    pkg_summary,
    groupUniqArray(pkg_packager_email) AS packagers,
    pkg_url,
    pkg_license,
    pkg_group_,
    groupUniqArray(pkg_arch),
    acl_list
FROM last_packages
LEFT JOIN
(
    SELECT
        acl_for AS pkg_name,
        acl_list
    FROM last_acl
    WHERE acl_branch = '{branch}'
) AS Acl USING pkg_name
WHERE pkgset_name = '{branch}'
    AND pkg_sourcepackage IN {src}
    {archs}
    AND pkg_name NOT LIKE '%%-debuginfo'
GROUP BY
    pkg_hash,
    pkg_name,
    pkg_version,
    pkg_release,
    pkg_summary,
    pkg_url,
    pkg_license,
    pkg_group_,
    acl_list
ORDER BY pkg_name
"""

    get_compare_info = """
SELECT
    pkg_name,
    pkg_version,
    pkg_release,
    Df.pkg_name,
    Df.pkg_version,
    Df.pkg_release
FROM
(
    SELECT
        pkg_name,
        pkg_version,
        pkg_release
    FROM static_last_packages
    WHERE pkgset_name = %(pkgset1)s
        AND pkg_sourcepackage = 1
        AND
        (
            pkg_name,
            pkg_version,
            pkg_release
        ) NOT IN
        (
            SELECT
                pkg_name,
                pkg_version,
                pkg_release
            FROM static_last_packages
            WHERE pkgset_name = %(pkgset2)s
                AND pkg_sourcepackage = 1
        )
        AND pkg_name IN
        (
            SELECT pkg_name
            FROM static_last_packages
            WHERE pkgset_name = %(pkgset2)s
                AND pkg_sourcepackage = 1
        )
) AS PkgSet2
INNER JOIN
(
    SELECT
        pkg_name,
        pkg_version,
        pkg_release
    FROM static_last_packages
    WHERE pkgset_name = %(pkgset2)s
        AND pkg_sourcepackage = 1
) AS Df USING pkg_name
UNION ALL
SELECT
    pkg_name,
    pkg_version,
    pkg_release,
    '',
    '',
    ''
FROM static_last_packages
WHERE pkgset_name = %(pkgset1)s
    AND pkg_sourcepackage = 1
    AND pkg_name NOT IN
    (
        SELECT pkg_name
        FROM static_last_packages
        WHERE pkgset_name = %(pkgset2)s
            AND pkg_sourcepackage = 1
    )
"""

    insert_pkgset_status = """
INSERT INTO RepositoryStatus (*) VALUES
"""

    get_pkgset_status = """
SELECT
    pkgset_name,
    argMax(rs_pkgset_name_bugzilla, ts) AS pkgset_name_bugzilla,
    argMax(rs_start_date, ts) AS start_date,
    argMax(rs_end_date, ts) AS end_date,
    argMax(rs_show, ts) AS show,
    argMax(rs_description_ru, ts) AS desc_ru,
    argMax(rs_description_en, ts) AS desc_en,
    argMax(rs_mailing_list, ts) AS mailing_list,
    argMax(rs_mirrors_json, ts) AS mirrors_json
FROM RepositoryStatus
GROUP BY pkgset_name
"""

    get_active_pkgsets = """
SELECT pkgset_name
FROM
(
    SELECT
        pkgset_name,
        argMax(rs_show, ts) AS show
    FROM RepositoryStatus
    GROUP BY pkgset_name
)
WHERE show = 1
"""

    get_branch_has_active_images = """
SELECT img_branch, count(img_edition)
FROM (
    SELECT
        img_branch,
        img_edition,
        argMax(img_show, ts) AS img_show
    FROM ImageStatus
    GROUP BY
        img_branch,
        img_edition
)
WHERE img_show == 'show'
GROUP BY img_branch
"""

    get_repository_statistics = """
SELECT branch, branch_date, stats
FROM lv_repository_statistics
{branch}
"""

    get_packages_by_uuid = """
WITH
pkg_hashes AS (
    SELECT pkg_hash
    FROM Packages
    WHERE pkg_hash IN (
        select pkg_hash
        FROM PackageSet
        WHERE pkgset_uuid = '{uuid}'
    )
),
pkg_changelogs AS (
    SELECT
        chlog_hash,
        chlog_text
    FROM Changelog
    WHERE chlog_hash IN (
        SELECT pkg_changelog.hash[1] AS hash
        FROM Packages
        WHERE pkg_hash IN (SELECT * FROM pkg_hashes)
    )
)
SELECT DISTINCT
    pkg_hash,
    pkg_name,
    pkg_version,
    pkg_release,
    pkg_arch,
    if(pkg_sourcepackage = 1, 'source', 'binary') as sourcerpm,
    pkg_summary,
    pkg_buildtime,
    pkg_changelog.date[1] AS date,
    pkg_changelog.name[1] as name,
    pkg_changelog.evr[1] AS evr,
    CHLG.chlog_text
FROM Packages
LEFT JOIN (
    SELECT * FROM pkg_changelogs
) AS CHLG ON CHLG.chlog_hash = pkg_changelog.hash[1]
WHERE pkg_hash IN (SELECT pkg_hash FROM pkg_hashes)
"""


sql = SQL()
