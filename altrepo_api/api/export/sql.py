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

    truncate_tmp_table = """
TRUNCATE TABLE {tmp_table}
"""

    insert_into_tmp_table = """
INSERT INTO {tmp_table} (*) VALUES
"""

    drop_tmp_table = """
DROP TABLE {tmp_table}
"""

    get_branch_stat = """
SELECT
    any(pkgset_date),
    groupUniqArray((pkg_arch, cnt))
FROM lv_pkgset_stat
WHERE pkgset_name = '{branch}'
"""

    get_branch_pkg_info = """
WITH
bin_archs AS (
    SELECT pkg_arch
    FROM lv_pkgset_stat
    WHERE pkgset_name = '{branch}'
        AND pkg_arch != 'srpm'
),
src_hashes AS
(
    SELECT pkg_hash
    FROM static_last_packages
    WHERE pkg_sourcepackage = 1
        AND pkgset_name = '{branch}'
),
src_specfiles AS
(
    SELECT
        pkg_hash AS src_hash,
        specfile_name
    FROM Specfiles
    WHERE pkg_hash IN (SELECT * FROM src_hashes)
),
bin_packages AS
(
    SELECT
        pkg_srcrpm_hash AS hash,
        pkg_name AS name,
        pkg_epoch AS epoch,
        pkg_version AS version,
        pkg_release AS release,
        any(pkg_summary) AS summary,
        groupUniqArray(pkg_arch) AS archs
    FROM Packages
    WHERE pkg_sourcepackage = 0
        AND pkg_arch IN (SELECT * FROM bin_archs)
        AND pkg_srcrpm_hash IN (SELECT * FROM src_hashes)
    GROUP BY pkg_srcrpm_hash, pkg_name, pkg_epoch, pkg_version, pkg_release
)
SELECT DISTINCT
    pkg_name,
    pkg_epoch,
    pkg_version,
    pkg_release,
    pkg_group_,
    pkg_url,
    pkg_summary,
    pkg_license,
    pkg_packager_email,
    SPC.specfile_name,
    BPKG.bin_pkgs
FROM Packages
LEFT JOIN
(
    SELECT src_hash, specfile_name
    FROM src_specfiles
) AS SPC ON SPC.src_hash = Packages.pkg_hash
LEFT JOIN
(
    SELECT
        hash,
        groupArray((name, epoch, version, release, summary, archs)) AS bin_pkgs
    FROM bin_packages
    GROUP BY hash
) AS BPKG ON BPKG.hash = Packages.pkg_hash
WHERE pkg_sourcepackage = 1
    AND pkg_hash IN (SELECT * FROM src_hashes)
"""

    get_branch_source_packages = """
SELECT
    toString(pkg_hash),
    pkg_name,
    pkg_buildtime
FROM Packages
WHERE pkg_hash IN (
    SELECT pkg_hash
    FROM static_last_packages
    WHERE pkgset_name = '{branch}'
      AND pkg_sourcepackage = 1
)
"""

    get_branch_binary_packages = """
SELECT DISTINCT
    pkg_name,
    pkg_epoch,
    pkg_version,
    pkg_release,
    pkg_arch,
    pkg_disttag,
    pkg_buildtime,
    SRC.pkg_name AS pkg_source
FROM Packages
LEFT JOIN
(
    SELECT pkg_hash, pkg_name
    FROM static_last_packages
    WHERE pkgset_name = '{branch}'
        AND pkg_sourcepackage = 1
) AS SRC ON SRC.pkg_hash = Packages.pkg_srcrpm_hash
WHERE pkg_hash IN
(
    SELECT pkg_hash
    FROM static_last_packages
    WHERE pkgset_name = '{branch}'
        AND pkg_sourcepackage = 0
)
{arch_clause}
ORDER BY pkg_arch, pkg_name
"""

    get_packages_descriptions = """
SELECT DISTINCT
    pkg_name,
    pkg_url,
    pkg_summary,
    pkg_description,
    arrayStringConcat(arrayPopBack(arrayPopBack(splitByChar('-', pkg_sourcerpm))), '-') AS src_pkg_name
FROM last_packages
WHERE pkgset_name IN {branches}
    AND pkg_name NOT LIKE '%%-debuginfo'
    AND pkg_name NOT LIKE 'i586-%%'
ORDER BY pkg_name
"""

    get_done_tasks = """
WITH task_and_repo AS (
    SELECT DISTINCT
        task_id,
        task_repo
    FROM Tasks
    WHERE task_repo IN {branches}
)
SELECT
    task_id,
    task_prev,
    task_repo,
    task_changed
FROM TaskStates
LEFT JOIN (SELECT * FROM task_and_repo) AS TR USING task_id
WHERE task_state = 'DONE' and task_id IN (
    SELECT task_id FROM task_and_repo
)
ORDER BY task_changed DESC
"""

    get_branch_history = """
SELECT
    pkgset_nodename,
    pkgset_date,
    toUInt32(pkgset_kv.v[indexOf(pkgset_kv.k, 'task')])
FROM PackageSetName
WHERE pkgset_depth = 0 AND pkgset_nodename IN {branches}
ORDER BY pkgset_date DESC
"""


sql = SQL()
