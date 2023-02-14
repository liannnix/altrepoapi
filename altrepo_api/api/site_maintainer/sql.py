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

    get_maintainer_repocop = """
SELECT
    pkg_name,
    pkg_version,
    pkg_release,
    pkg_arch,
    rc_srcpkg_name,
    pkgset_name,
    rc_test_name,
    argMax(rc_test_status, rc_test_date),
    argMax(rc_test_message, rc_test_date),
    max(rc_test_date)
FROM PackagesRepocop
WHERE rc_test_status NOT IN ('ok', 'skip')
    AND (rc_srcpkg_name, rc_srcpkg_version, rc_srcpkg_release, pkgset_name) IN
(SELECT DISTINCT
    pkg_name,
    pkg_version,
    pkg_release,
    pkgset_name
FROM last_packages
WHERE pkgset_name = '{branch}'
    AND pkg_sourcepackage = 1
    AND (pkg_packager_email LIKE '{maintainer_nickname}@%'
    OR pkg_packager_email LIKE '{maintainer_nickname} at%'
    OR pkg_packager LIKE '%{maintainer_nickname}@%')
)
GROUP BY
    pkg_name,
    pkg_version,
    pkg_release,
    pkg_arch,
    rc_srcpkg_name,
    pkgset_name,
    rc_test_name
ORDER BY
    pkg_name ASC,
    pkg_arch ASC
"""

    get_repocop_by_last_acl_with_group = """
SELECT
    pkg_name,
    pkg_version,
    pkg_release,
    pkg_arch,
    rc_srcpkg_name,
    pkgset_name,
    rc_test_name,
    argMax(rc_test_status, rc_test_date),
    argMax(rc_test_message, rc_test_date),
    max(rc_test_date)
FROM PackagesRepocop
WHERE rc_test_status NOT IN ('ok', 'skip')
    AND (rc_srcpkg_name, rc_srcpkg_version, rc_srcpkg_release, pkgset_name) IN
(SELECT DISTINCT
    pkg_name,
    pkg_version,
    pkg_release,
    pkgset_name
FROM last_packages
WHERE pkgset_name = '{branch}'
    AND pkg_sourcepackage = 1
    AND pkg_name IN (
        SELECT pkgname
            FROM last_acl_with_groups
            WHERE acl_user = '{maintainer_nickname}'
                AND acl_branch = 'sisyphus'
                AND order_u = 1
                {order_g}
    )
)
GROUP BY
    pkg_name,
    pkg_version,
    pkg_release,
    pkg_arch,
    rc_srcpkg_name,
    pkgset_name,
    rc_test_name
ORDER BY
    pkg_name ASC,
    pkg_arch ASC
"""

    get_repocop_by_nick_acl = """
    SELECT
        pkg_name,
        pkg_version,
        pkg_release,
        pkg_arch,
        rc_srcpkg_name,
        pkgset_name,
        rc_test_name,
        argMax(rc_test_status, rc_test_date),
        argMax(rc_test_message, rc_test_date),
        max(rc_test_date)
    FROM PackagesRepocop
    WHERE rc_test_status NOT IN ('ok', 'skip')
        AND (rc_srcpkg_name, rc_srcpkg_version, rc_srcpkg_release, pkgset_name) IN
    (SELECT DISTINCT
        pkg_name,
        pkg_version,
        pkg_release,
        pkgset_name
    FROM last_packages
    WHERE pkgset_name = '{branch}'
        AND pkg_sourcepackage = 1
        AND pkg_name IN (
            SELECT acl_for
                FROM last_acl_stage1
                WHERE acl_branch = 'sisyphus'
                    AND has(acl_list, '{maintainer_nickname}')
        )
    )
    GROUP BY
        pkg_name,
        pkg_version,
        pkg_release,
        pkg_arch,
        rc_srcpkg_name,
        pkgset_name,
        rc_test_name
    ORDER BY
        pkg_name ASC,
        pkg_arch ASC
    """

    get_repocop_by_nick_or_group_acl = """
WITH
(
    SELECT groupUniqArray(acl_for)
    FROM last_acl_stage1
    WHERE has(acl_list, '{maintainer_nickname}')
        AND acl_for LIKE ('@%')
        AND acl_branch = 'sisyphus'
) AS acl_group
SELECT
    pkg_name,
    pkg_version,
    pkg_release,
    pkg_arch,
    rc_srcpkg_name,
    pkgset_name,
    rc_test_name,
    argMax(rc_test_status, rc_test_date),
    argMax(rc_test_message, rc_test_date),
    max(rc_test_date)
FROM PackagesRepocop
WHERE rc_test_status NOT IN ('ok', 'skip')
    AND (rc_srcpkg_name, rc_srcpkg_version, rc_srcpkg_release, pkgset_name) IN
(SELECT DISTINCT
    pkg_name,
    pkg_version,
    pkg_release,
    pkgset_name
FROM last_packages
WHERE pkgset_name = '{branch}'
    and pkg_sourcepackage = 1
    and pkg_name in (
        SELECT acl_for
            FROM last_acl_stage1
            WHERE acl_branch = 'sisyphus'
                AND (has(acl_list, '{maintainer_nickname}')
                OR hasAny(acl_list, acl_group))
    )
)
GROUP BY
    pkg_name,
    pkg_version,
    pkg_release,
    pkg_arch,
    rc_srcpkg_name,
    pkgset_name,
    rc_test_name
ORDER BY
    pkg_name ASC,
    pkg_arch ASC
"""

    get_beehive_errors_by_maintainer = """
WITH
last_bh_updated AS
(
    SELECT
        pkgset_name,
        bh_arch as arch,
        max(bh_updated) AS updated
    FROM BeehiveStatus
    WHERE pkgset_name = '{branch}'
    GROUP BY
        pkgset_name,
        bh_arch
),
maintainer_packages AS
(
    SELECT
        pkg_hash,
        pkg_epoch
    FROM last_packages
    WHERE pkg_packager_email LIKE '{maintainer_nickname}@%'
        AND pkgset_name = '{branch}'
        AND pkg_sourcepackage = 1
)
SELECT
    pkg_hash,
    pkgset_name,
    pkg_name,
    pkg_version,
    pkg_release,
    bh_arch,
    bh_build_time,
    bh_updated,
    bh_ftbfs_since,
    Pkg.pkg_epoch
FROM BeehiveStatus
LEFT JOIN
(SELECT pkg_hash, pkg_epoch FROM maintainer_packages) AS Pkg USING (pkg_hash)
WHERE pkgset_name = '{branch}'
    AND bh_status = 'error'
    AND (bh_arch, bh_updated) IN
    (
        SELECT arch, updated FROM last_bh_updated
    )
    AND pkg_hash IN
    (
        SELECT pkg_hash FROM maintainer_packages
    )
ORDER BY pkg_name
"""

    get_beehive_errors_by_nick_acl = """
WITH
last_bh_updated AS
(
    SELECT
        pkgset_name,
        bh_arch as arch,
        max(bh_updated) AS updated
    FROM BeehiveStatus
    WHERE pkgset_name = '{branch}'
    GROUP BY
        pkgset_name,
        bh_arch
),
maintainer_packages AS
(
    SELECT
        pkg_hash,
        pkg_epoch
    FROM last_packages
    WHERE pkg_sourcepackage = 1
        AND pkgset_name = '{branch}'
        AND pkg_name IN (
    SELECT acl_for
    FROM last_acl_stage1
    WHERE acl_branch = 'sisyphus'
        AND has(acl_list, '{maintainer_nickname}'))
)
SELECT
    pkg_hash,
    pkgset_name,
    pkg_name,
    pkg_version,
    pkg_release,
    bh_arch,
    bh_build_time,
    bh_updated,
    bh_ftbfs_since,
    Pkg.pkg_epoch
FROM BeehiveStatus
LEFT JOIN
(SELECT pkg_hash, pkg_epoch FROM maintainer_packages) AS Pkg USING (pkg_hash)
WHERE pkgset_name = '{branch}'
    AND bh_status = 'error'
    AND (bh_arch, bh_updated) IN
    (
        SELECT arch, updated FROM last_bh_updated
    )
    AND pkg_hash IN
    (
        SELECT pkg_hash FROM maintainer_packages
    )
ORDER BY pkg_name
"""

    get_beehive_errors_by_last_acl_with_group = """
WITH
last_bh_updated AS
(
    SELECT
        pkgset_name,
        bh_arch as arch,
        max(bh_updated) AS updated
    FROM BeehiveStatus
    WHERE pkgset_name = '{branch}'
    GROUP BY
        pkgset_name,
        bh_arch
),
maintainer_packages AS
(
    SELECT
        pkg_hash,
        pkg_epoch
    FROM last_packages
    WHERE pkg_sourcepackage = 1
        AND pkgset_name = '{branch}'
        AND pkg_name IN (
            SELECT pkgname
            FROM last_acl_with_groups
            WHERE acl_branch = 'sisyphus'
                AND acl_user = '{maintainer_nickname}'
                AND order_u = 1
                {order_g}
            )
)
SELECT
    pkg_hash,
    pkgset_name,
    pkg_name,
    pkg_version,
    pkg_release,
    bh_arch,
    bh_build_time,
    bh_updated,
    bh_ftbfs_since,
    Pkg.pkg_epoch
FROM BeehiveStatus
LEFT JOIN
(SELECT pkg_hash, pkg_epoch FROM maintainer_packages) AS Pkg USING (pkg_hash)
WHERE pkgset_name = '{branch}'
    AND bh_status = 'error'
    AND (bh_arch, bh_updated) IN
    (
        SELECT arch, updated FROM last_bh_updated
    )
    AND pkg_hash IN
    (
        SELECT pkg_hash FROM maintainer_packages
    )
ORDER BY pkg_name
"""

    get_beehive_errors_by_nick_or_group_acl = """
WITH
last_bh_updated AS
(
    SELECT
        pkgset_name,
        bh_arch as arch,
        max(bh_updated) AS updated
    FROM BeehiveStatus
    WHERE pkgset_name = '{branch}'
    GROUP BY
        pkgset_name,
        bh_arch
),
(
    SELECT groupUniqArray(acl_for)
    FROM last_acl_stage1
    WHERE has(acl_list, '{maintainer_nickname}')
        AND acl_for LIKE ('@%')
        AND acl_branch = 'sisyphus'
) AS acl_group,
maintainer_packages AS
(
    SELECT
        pkg_hash,
        pkg_epoch
    FROM last_packages
    WHERE pkg_sourcepackage = 1
        AND pkgset_name = '{branch}'
        AND pkg_name IN (
            SELECT acl_for
            FROM last_acl_stage1
            WHERE acl_branch = 'sisyphus'
                AND (has(acl_list, '{maintainer_nickname}')
                OR hasAny(acl_list, acl_group))
        )
)
SELECT
    pkg_hash,
    pkgset_name,
    pkg_name,
    pkg_version,
    pkg_release,
    bh_arch,
    bh_build_time,
    bh_updated,
    bh_ftbfs_since,
    Pkg.pkg_epoch
FROM BeehiveStatus
LEFT JOIN
(SELECT pkg_hash, pkg_epoch FROM maintainer_packages) AS Pkg USING (pkg_hash)
WHERE pkgset_name = '{branch}'
    AND bh_status = 'error'
    AND (bh_arch, bh_updated) IN
    (
        SELECT arch, updated FROM last_bh_updated
    )
    AND pkg_hash IN
    (
        SELECT pkg_hash FROM maintainer_packages
    )
ORDER BY pkg_name
"""

    get_all_maintaners = """
SELECT
    argMax(pkg_packager, cnt) AS name,
    argMax(packager_nick, cnt) AS nick,
    sum(cnt) AS count
FROM
(
    SELECT DISTINCT
        pkg_packager,
        substring(pkg_packager_email, 1, position(pkg_packager_email, '@') - 1) AS packager_nick,
        countDistinct(pkg_hash) AS cnt
    FROM last_packages
    WHERE pkgset_name = '{branch}'
        AND pkg_sourcepackage = 1
    GROUP BY
        pkg_packager,
        packager_nick
)
{where_clause}
GROUP BY packager_nick ORDER by name
"""

    get_maintainer_branches = """
SELECT
    pkgset_name,
    countDistinct(pkg_hash)
FROM last_packages
WHERE pkg_packager_email LIKE '{maintainer_nickname}@%'
    AND pkg_sourcepackage = 1
GROUP BY
    pkgset_name
"""

    get_maintainer_pkg = """
SELECT
    pkg_name,
    pkg_buildtime,
    pkg_url,
    pkg_summary,
    pkg_version,
    pkg_release
FROM last_packages
WHERE pkg_packager_email LIKE '{maintainer_nickname}@%'
    AND pkgset_name = '{branch}'
    AND pkg_sourcepackage = 1
GROUP BY
    pkg_name,
    pkg_version,
    pkg_release,
    pkg_buildtime,
    pkg_url,
    pkg_summary
ORDER BY pkg_buildtime DESC
"""

    get_maintainer_pkg_by_nick_or_group_acl = """
WITH
(
    SELECT groupUniqArray(acl_for)
    FROM last_acl_stage1
    WHERE has(acl_list, '{maintainer_nickname}')
        AND acl_for LIKE ('@%')
        AND acl_branch = 'sisyphus'
) AS acl_group
SELECT
    pkg_name,
    pkg_buildtime,
    pkg_url,
    pkg_summary,
    pkg_version,
    pkg_release
FROM last_packages
WHERE pkg_sourcepackage = 1
      AND pkgset_name = '{branch}'
      AND pkg_name IN (
        SELECT acl_for
        FROM last_acl_stage1
        WHERE acl_branch = 'sisyphus'
          AND (has(acl_list, '{maintainer_nickname}')
          OR hasAny(acl_list, acl_group))
    )
GROUP BY
    pkg_name,
    pkg_buildtime,
    pkg_url,
    pkg_summary,
    pkg_version,
    pkg_release
ORDER BY pkg_buildtime DESC
"""

    get_maintainer_pkg_by_nick_leader_acl = """
SELECT
    pkg_name,
    pkg_buildtime,
    pkg_url,
    pkg_summary,
    pkg_version,
    pkg_release
FROM last_packages
WHERE pkg_sourcepackage = 1
      AND pkgset_name = '{branch}'
      AND pkg_name IN (
        SELECT pkgname
        FROM last_acl_with_groups
        WHERE acl_branch = 'sisyphus'
          AND acl_user = '{maintainer_nickname}'
          AND order_u = 1
          AND order_g = 0
    )
GROUP BY
    pkg_name,
    pkg_buildtime,
    pkg_url,
    pkg_summary,
    pkg_version,
    pkg_release
ORDER BY pkg_buildtime DESC
"""

    get_maintainer_pkg_by_nick_acl = """
SELECT
    pkg_name,
    pkg_buildtime,
    pkg_url,
    pkg_summary,
    pkg_version,
    pkg_release
FROM last_packages
WHERE pkg_sourcepackage = 1
      AND pkgset_name = '{branch}'
      AND pkg_name IN (
        SELECT acl_for
        FROM last_acl_stage1
        WHERE acl_branch = 'sisyphus'
          AND has(acl_list, '{maintainer_nickname}')
    )
GROUP BY
    pkg_name,
    pkg_buildtime,
    pkg_url,
    pkg_summary,
    pkg_version,
    pkg_release
ORDER BY pkg_buildtime DESC
"""

    get_maintainer_pkg_by_nick_leader_and_group_acl = """
SELECT
    pkg_name,
    pkg_buildtime,
    pkg_url,
    pkg_summary,
    pkg_version,
    pkg_release
FROM last_packages
WHERE pkg_sourcepackage = 1
      AND pkgset_name = '{branch}'
      AND pkg_name IN (
        SELECT pkgname
        FROM last_acl_with_groups
        WHERE acl_user = '{maintainer_nickname}'
            AND acl_branch = 'sisyphus'
            AND order_u = 1
)
GROUP BY
    pkg_name,
    pkg_buildtime,
    pkg_url,
    pkg_summary,
    pkg_version,
    pkg_release
ORDER BY pkg_buildtime DESC
"""

    get_watch_by_last_acl_with_group = """
WITH (
    SELECT max(toDate(date_update))
    FROM PackagesWatch
) AS max_watch_date
SELECT
    argMax(pkg_name, date_update),
    argMax(old_version, date_update),
    argMax(new_version, date_update),
    argMax(url, date_update),
    max(date_update)
FROM PackagesWatch
WHERE pkg_name IN (
    SELECT pkgname
    FROM last_acl_with_groups
    WHERE acl_user = '{maintainer_nickname}'
        AND acl_branch = 'sisyphus'
        AND order_u = 1
    )
    AND toDate(date_update) = max_watch_date
GROUP BY
    pkg_name,
    url
ORDER BY pkg_name ASC
"""

    get_watch_by_last_acl = """
WITH (
    SELECT max(toDate(date_update))
    FROM PackagesWatch
) AS max_watch_date
SELECT
    argMax(pkg_name, date_update),
    argMax(old_version, date_update),
    argMax(new_version, date_update),
    argMax(url, date_update),
    max(date_update)
FROM PackagesWatch
WHERE acl = '{maintainer_nickname}'
    AND toDate(date_update) = max_watch_date
GROUP BY
    pkg_name,
    url
ORDER BY pkg_name ASC
"""

    get_watch_by_nick_acl = """
WITH (
    SELECT max(toDate(date_update))
    FROM PackagesWatch
) AS max_watch_date
SELECT
    argMax(pkg_name, date_update),
    argMax(old_version, date_update),
    argMax(new_version, date_update),
    argMax(url, date_update),
    max(date_update)
FROM PackagesWatch
WHERE pkg_name IN (
    SELECT acl_for
    FROM last_acl_stage1
    WHERE acl_branch = 'sisyphus'
        AND has(acl_list, '{maintainer_nickname}')
    )
    AND toDate(date_update) = max_watch_date
GROUP BY
    pkg_name,
    url
ORDER BY pkg_name ASC
"""

    get_watch_by_nick_or_group_acl = """
WITH
(
    SELECT groupUniqArray(acl_for)
    FROM last_acl_stage1
    WHERE has(acl_list, '{maintainer_nickname}')
        AND acl_for LIKE ('@%')
        AND acl_branch = 'sisyphus'
) AS acl_group,
(
    SELECT max(toDate(date_update))
    FROM PackagesWatch
) AS max_watch_date
SELECT
    argMax(pkg_name, date_update),
    argMax(old_version, date_update),
    argMax(new_version, date_update),
    argMax(url, date_update),
    max(date_update)
FROM PackagesWatch
WHERE pkg_name IN (
    SELECT acl_for
    FROM last_acl_stage1
    WHERE acl_branch = 'sisyphus'
        AND (has(acl_list, '{maintainer_nickname}')
        OR hasAny(acl_list, acl_group))
    )
    AND toDate(date_update) = max_watch_date
GROUP BY
    pkg_name,
    url
ORDER BY pkg_name ASC
"""

    get_watch_by_packager = """
WITH (
    SELECT max(toDate(date_update))
    FROM PackagesWatch
) AS max_watch_date
SELECT
    argMax(pkg_name, date_update),
    argMax(old_version, date_update),
    argMax(new_version, date_update),
    argMax(url, date_update),
    max(date_update)
FROM PackagesWatch
WHERE pkg_name IN (
    SELECT pkg_name
    FROM last_packages
    WHERE pkgset_name = 'sisyphus'
        AND pkg_sourcepackage = 1
        AND (pkg_packager_email LIKE '{maintainer_nickname}@%'
            OR pkg_packager_email LIKE '{maintainer_nickname} at%'
            OR pkg_packager LIKE '%{maintainer_nickname}@%')
    )
    AND toDate(date_update) = max_watch_date
GROUP BY
    pkg_name,
    url
ORDER BY pkg_name ASC
"""


sql = SQL()
