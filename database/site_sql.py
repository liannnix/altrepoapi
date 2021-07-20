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


sitesql = SQL()
