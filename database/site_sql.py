from dataclasses import dataclass

@dataclass(frozen=True)
class SQL:
    create_tmp_table = """
CREATE TEMPORARY TABLE {tmp_table} {columns}
"""

    select_all_tmp_table = """
SELECT * FROM {tmp_table}
"""

    get_repo_packages = """
SELECT
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
    FROM Changelog_buffer
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
FROM Packages_buffer
WHERE pkg_hash = {pkghash}
"""

    get_pkg_maintaners = """
SELECT DISTINCT
    pkg_packager,
    pkg_packager_email
FROM Packages_buffer
WHERE pkg_name = '{name}'
    AND pkg_sourcepackage = 1
"""

    get_binary_pkgs = """
SELECT DISTINCT pkg_name
FROM Packages_buffer
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
    pkg_release
FROM last_packages
WHERE pkg_name = '{name}'
    AND pkg_sourcepackage = 0
"""


sitesql = SQL()
