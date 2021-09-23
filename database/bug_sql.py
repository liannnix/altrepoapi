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
    WHERE pkg_name = %(srcpkg_name)s
        AND pkg_sourcepackage = 1
)
    AND pkg_sourcepackage = 0
"""

    get_bugzilla_info_by_srcpkg = """
WITH bugs AS
    (
        SELECT DISTINCT
            bz_id,
            bz_component
        FROM Bugzilla
        WHERE bz_component IN {packages}
    )
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
        argMax(bz_assignee, ts),
        argMax(bz_reporter, ts),
        argMax(bz_summary, ts),
        max(ts)
    FROM Bugzilla
    WHERE bz_id IN (
        SELECT bz_id
        FROM bugs
    )
    GROUP BY bz_id
    ORDER BY bz_id DESC
)
WHERE bz_component IN (
    SELECT bz_component
    FROM bugs
)
"""

    get_bugzilla_info_by_maintainer = """
WITH bugs AS
    (
        SELECT DISTINCT
            bz_id,
            bz_assignee
        FROM Bugzilla
        WHERE (bz_assignee LIKE '{maintainer_nickname}'
            OR bz_assignee LIKE '{maintainer_nickname}@%')
    )
SELECT *
FROM
(
    SELECT
        bz_id,
        argMax(bz_status, ts),
        argMax(bz_resolution, ts),
        argMax(bz_severity, ts),
        argMax(bz_product, ts),
        argMax(bz_component, ts),
        argMax(bz_assignee, ts) AS bz_assignee,
        argMax(bz_reporter, ts),
        argMax(bz_summary, ts),
        max(ts)
    FROM Bugzilla
    WHERE bz_id IN (
        SELECT bz_id
        FROM bugs
    )
    GROUP BY bz_id
    ORDER BY bz_id DESC
)
WHERE bz_assignee IN (
    SELECT bz_assignee
    FROM bugs
)
"""


bugsql = SQL()
