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


pkgsetsql = SQL()
