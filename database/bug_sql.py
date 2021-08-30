from dataclasses import dataclass


@dataclass(frozen=True)
class SQL:

    get_pkg_name_by_srcpkg = """
SELECT DISTINCT pkg_name
FROM Packages_buffer
WHERE (pkg_srcrpm_hash IN (
    SELECT DISTINCT pkg_hash
    FROM Packages_buffer
    WHERE (pkg_name = '{srcpkg_name}') AND (pkg_sourcepackage = 1)
)) AND (pkg_sourcepackage = 0)
"""

    get_bugzilla_info_by_srcpkg = """
SELECT
    bz_id,
    argMax((bz_status, bz_resolution, bz_severity, bz_product, bz_component, bz_assignee, bz_reporter, bz_summary), ts)
FROM Bugzilla
WHERE multiMatchAny(bz_component, {packages})
GROUP BY bz_id
ORDER BY bz_id DESC
"""

    get_bugzilla_info_by_maintainer = """
SELECT
    bz_id,
    argMax((bz_status, bz_resolution, bz_severity, bz_product, bz_component, bz_assignee, bz_reporter, bz_summary), ts)
FROM Bugzilla
WHERE (bz_assignee LIKE '{maintainer_nickname}'
    OR bz_assignee LIKE '{maintainer_nickname}%')
GROUP BY bz_id
ORDER BY bz_id DESC
"""

bugsql = SQL()