from dataclasses import dataclass

@dataclass(frozen=True)
class SQL:
    get_repo_packages = """
SELECT
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
    AND pkg_arch IN {archs}
    AND pkg_name NOT LIKE '%%-debuginfo'
GROUP BY
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


pkgsetsql = SQL()
