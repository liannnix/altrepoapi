# ALTRepo API
# Copyright (C) 2021-2022  BaseALT Ltd

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
        argMax(bz_component, ts) AS bz_cmp,
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
) AS bugzilla
LEFT JOIN
(
    SELECT
        argMax(src_pkg_name, buildtime),
        bin_pkg_name
    FROM PackagesSourceAndBinaries
    GROUP BY bin_pkg_name
) AS TT ON TT.bin_pkg_name = bugzilla.bz_cmp
WHERE bz_assignee IN (
    SELECT bz_assignee
    FROM bugs
) 
"""

    get_bugzilla_info_by_last_acl_with_group = """
WITH acl_package AS 
(
SELECT DISTINCT bin_pkg_name
FROM PackagesSourceAndBinaries
WHERE src_pkg_name IN (
    SELECT pkgname
    FROM last_acl_with_groups
    WHERE acl_branch = 'sisyphus'
        AND acl_user = '{maintainer_nickname}'
        AND order_u = 1
        {order_g}
    )
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
        argMax(bz_component, ts) AS bz_cmp,
        argMax(bz_assignee, ts) AS bz_assignee,
        argMax(bz_reporter, ts),
        argMax(bz_summary, ts),
        max(ts)
    FROM Bugzilla
    WHERE bz_component IN (
        SELECT bin_pkg_name
        FROM acl_package
    )
    GROUP BY bz_id
    ORDER BY bz_id DESC
) AS bugzilla
LEFT JOIN
(
    SELECT
        argMax(src_pkg_name, buildtime),
        bin_pkg_name
    FROM PackagesSourceAndBinaries
    GROUP BY bin_pkg_name
) AS TT ON TT.bin_pkg_name = bugzilla.bz_cmp
"""

    get_beehive_errors_by_nick_or_group_acl = """
WITH acl_package AS
(
SELECT DISTINCT bin_pkg_name
FROM PackagesSourceAndBinaries
WHERE src_pkg_name IN (
    SELECT acl_for
    FROM last_acl_stage1
    WHERE acl_branch = 'sisyphus'
        AND has(acl_list, '{maintainer_nickname}')
    )
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
        argMax(bz_component, ts) AS bz_cmp,
        argMax(bz_assignee, ts) AS bz_assignee,
        argMax(bz_reporter, ts),
        argMax(bz_summary, ts),
        max(ts)
    FROM Bugzilla
    WHERE bz_component IN (
        SELECT bin_pkg_name
        FROM acl_package
    )
    GROUP BY bz_id
    ORDER BY bz_id DESC
) AS bugzilla
LEFT JOIN
(
    SELECT
        argMax(src_pkg_name, buildtime),
        bin_pkg_name
    FROM PackagesSourceAndBinaries
    GROUP BY bin_pkg_name
) AS TT ON TT.bin_pkg_name = bugzilla.bz_cmp
"""

    get_bugzilla_info_by_nick_acl = """
WITH
(
    SELECT groupUniqArray(acl_for)
    FROM last_acl_stage1
    WHERE has(acl_list, '{maintainer_nickname}')
        AND acl_for LIKE ('@%')
        AND acl_branch = 'sisyphus'
) AS acl_group,
acl_package AS (
    SELECT DISTINCT bin_pkg_name
    FROM PackagesSourceAndBinaries
    WHERE src_pkg_name IN (
        SELECT acl_for
            FROM last_acl_stage1
            WHERE acl_branch = 'sisyphus'
                AND (has(acl_list, '{maintainer_nickname}')
                OR hasAny(acl_list, acl_group))
        )
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
        argMax(bz_component, ts) AS bz_cmp,
        argMax(bz_assignee, ts) AS bz_assignee,
        argMax(bz_reporter, ts),
        argMax(bz_summary, ts),
        max(ts)
    FROM Bugzilla
    WHERE bz_component IN (
        SELECT bin_pkg_name
        FROM acl_package
    )
    GROUP BY bz_id
    ORDER BY bz_id DESC
) AS bugzilla
LEFT JOIN
(
    SELECT
        argMax(src_pkg_name, buildtime),
        bin_pkg_name
    FROM PackagesSourceAndBinaries
    GROUP BY bin_pkg_name
) AS TT ON TT.bin_pkg_name = bugzilla.bz_cmp
"""


sql = SQL()
