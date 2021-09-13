from dataclasses import dataclass


@dataclass(frozen=True)
class SQL:

    get_pkg_name_by_srcpkg = """
SELECT DISTINCT pkg_name
FROM Packages_buffer
WHERE pkg_srcrpm_hash IN
(
    SELECT DISTINCT pkg_hash
    FROM Packages_buffer
    WHERE pkg_name = '{srcpkg_name}'
        AND pkg_sourcepackage = 1
)
    AND pkg_sourcepackage = 0
"""

    get_bugzilla_info_by_srcpkg = """
SELECT *
FROM
(

    SELECT
        bz_id,
        argMax(bz_status, ts),
        argMax(bz_resolution, ts),
        argMax(bz_severity, ts),
        argMax(bz_product, ts),
        argMax(bz_component, ts) AS bz_component,
        argMax(bz_assignee, ts) AS bz_assignee,
        argMax(bz_reporter, ts),
        argMax(bz_summary, ts),
        max(ts)
    FROM Bugzilla
    GROUP BY bz_id
)
WHERE multiMatchAny(bz_component, {packages})
ORDER BY bz_id DESC
"""

    get_bugzilla_info_by_maintainer = """
SELECT *
FROM
(

    SELECT
        bz_id,
        argMax(bz_status, ts),
        argMax(bz_resolution, ts),
        argMax(bz_severity, ts),
        argMax(bz_product, ts),
        argMax(bz_component, ts) AS bz_component,
        argMax(bz_assignee, ts) AS bz_assignee,
        argMax(bz_reporter, ts),
        argMax(bz_summary, ts),
        max(ts)
    FROM Bugzilla
    GROUP BY bz_id
)
WHERE (bz_assignee LIKE '{maintainer_nickname}'
    OR bz_assignee LIKE '{maintainer_nickname}%')
ORDER BY bz_id DESC
"""

bugsql = SQL()
