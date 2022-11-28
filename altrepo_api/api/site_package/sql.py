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
    create_tmp_table = """
CREATE TEMPORARY TABLE {tmp_table} {columns}
"""

    select_all_tmp_table = """
SELECT * FROM {tmp_table}
"""

    insert_into_tmp_table = """
INSERT INTO {tmp_table} (*) VALUES
"""

    get_pkg_changelog = """
WITH pkg_changelog AS
    (
        SELECT
            pkg_hash,
            pkg_changelog.date AS date,
            pkg_changelog.name as name,
            extract(replaceOne(extract(pkg_changelog.name, '<(.+@?.+)>+'), ' at ', '@'), '(.*)@') AS nick,
            pkg_changelog.evr AS evr,
            pkg_changelog.hash AS hash
        FROM Packages
ARRAY JOIN pkg_changelog
        WHERE pkg_hash = %(pkghash)s
        LIMIT %(limit)s
    )
SELECT DISTINCT
    pkg_hash,
    date,
    name,
    nick,
    evr,
    Chg.chlog_text as text
FROM pkg_changelog
LEFT JOIN
(
    SELECT DISTINCT
        chlog_hash AS hash,
        chlog_text
    FROM Changelog_buffer
    WHERE chlog_hash IN (
        SELECT hash
        FROM pkg_changelog
    )
) AS Chg ON Chg.hash = pkg_changelog.hash
ORDER BY
    date DESC
"""

    get_pkg_info = """
SELECT
    pkg_name,
    pkg_version,
    pkg_release,
    pkg_arch,
    pkg_epoch,
    pkg_buildtime,
    pkg_url,
    pkg_license,
    pkg_summary,
    pkg_description,
    pkg_packager,
    substring(pkg_packager_email, 1, position(pkg_packager_email, '@') - 1) AS packager_nick,
    pkg_group_
FROM Packages
WHERE pkg_hash = {pkghash}
    {source}
"""

    get_task_gears_by_hash = """
SELECT DISTINCT
    task_repo,
    task_id,
    subtask_id,
    subtask_type,
    subtask_dir,
    subtask_tag_id,
    subtask_srpm_name,
    subtask_srpm_evr,
    task_changed
FROM Tasks
WHERE (task_id, subtask_id) IN
(
    SELECT
        task_id,
        subtask_id
    FROM TaskIterations
    WHERE titer_srcrpm_hash = {pkghash}
        OR has(titer_pkgs_hash, {pkghash})
)
AND (task_id, task_changed) IN
(
    SELECT task_id, task_changed
    FROM TaskStates
    WHERE task_state = 'DONE'
)
AND subtask_deleted != 1
ORDER BY task_changed DESC
"""

    get_task_bin_hshs_by_src_hsh = """
SELECT DISTINCT
    task_id,
    subtask_id,
    subtask_arch,
    titer_pkgs_hash
FROM TaskIterations
WHERE titer_srcrpm_hash = {pkghash}
    AND task_id = {task_id}
"""

    get_pkg_maintainers = """
SELECT pkg_changelog.name
FROM Packages
WHERE pkg_hash = {pkghash}
"""

    get_pkg_acl = """
SELECT acl_list
FROM last_acl
WHERE acl_for = '{name}'
    AND acl_branch = '{branch}'
"""

    get_pkg_versions = """
SELECT DISTINCT
    pkgset_name,
    pkg_version,
    pkg_release,
    toString(pkg_hash)
FROM static_last_packages
WHERE pkg_name = '{name}'
    AND pkg_sourcepackage = 1
"""

    get_pkg_binary_versions = """
SELECT DISTINCT
    pkgset_name,
    pkg_version,
    pkg_release,
    toString(pkg_hash)
FROM last_packages
WHERE pkg_name = '{name}'
    AND pkg_arch = '{arch}'
    AND pkg_sourcepackage = 0
"""

    get_pkg_dependencies = """
SELECT
    dp_name,
    dp_version,
    dp_flag
FROM Depends
WHERE pkg_hash = {pkghash}
    AND dp_type = 'require'
"""

    get_binary_pkgs = """
SELECT DISTINCT
    pkg_name,
    arrayReverseSort(groupUniqArray((pkg_arch, pkg_hash))),
    max(pkg_buildtime)
FROM Packages
WHERE (pkg_srcrpm_hash = {pkghash})
    AND (pkg_sourcepackage = 0)
    AND pkg_arch IN
    (
        SELECT pkg_arch
        FROM lv_pkgset_stat
        WHERE pkgset_name = '{branch}'
    )
GROUP BY pkg_name
ORDER BY pkg_name ASC
"""

    get_source_pkgs = """
SELECT DISTINCT
    pkg_name,
    pkg_hash
FROM Packages
WHERE pkg_hash IN (
    SELECT pkg_srcrpm_hash
    FROM Packages
    WHERE pkg_hash = {pkghash}
        AND pkg_sourcepackage = 0
    ORDER BY pkg_srcrpm_hash ASC
) AND pkg_sourcepackage = 1
"""

    get_last_bh_rebuild_status_by_hsh = """
WITH
last_bh_updated AS
(
    SELECT
        pkgset_name,
        bh_arch as arch,
        max(bh_updated) AS updated
    FROM BeehiveStatus
    WHERE pkgset_name = %(branch)s
    GROUP BY
        pkgset_name,
        bh_arch
)
SELECT
    bh_arch,
    bh_status,
    bh_build_time,
    bh_updated,
    bh_ftbfs_since
FROM BeehiveStatus
WHERE pkgset_name = %(branch)s
    AND pkg_hash = %(pkghash)s
    AND (bh_arch, bh_updated) IN
    (
        SELECT arch, updated FROM last_bh_updated
    )
"""

    get_deleted_package_task_by_src = """
SELECT
    task_id,
    any(subtask_id),
    max(task_changed),
    any(task_owner),
    any(subtask_userid)
FROM Tasks
WHERE subtask_deleted = 0
    AND subtask_type = 'delete'
    AND subtask_package = '{name}'
    AND task_repo = '{branch}'
    AND task_id IN
    (
        SELECT task_id
        FROM TaskStates
        WHERE task_state = 'DONE'
    )
GROUP BY task_id
"""

    get_deleted_package_task_by_bin = """
WITH
(
    SELECT DISTINCT pkg_name
    FROM Packages
    WHERE pkg_hash IN
    (
        SELECT any(pkg_srcrpm_hash)
        FROM Packages
        WHERE pkg_name = '{name}'
        AND pkg_sourcepackage = 0
    ) AND pkg_sourcepackage = 1
) AS src_package
SELECT
    task_id,
    any(subtask_id),
    max(task_changed),
    any(task_owner),
    any(subtask_userid)
FROM Tasks
WHERE subtask_deleted = 0
    AND subtask_type = 'delete'
    AND subtask_package = src_package
    AND task_repo = '{branch}'
    AND task_id IN
    (
        SELECT task_id
        FROM TaskStates
        WHERE task_state = 'DONE'
    )
GROUP BY task_id
"""

    get_delete_task_from_branch_history = """
WITH
delete_task_info  AS (
    SELECT
        task AS task_id,
        changed AS task_changed,
        hash
    FROM lv_branch_deleted_packages
    WHERE pkgset_name = '{branch}'
        AND pkg_name = '{name}'
)
SELECT DISTINCT
    task_id,
    0 AS subtask_id,
    task_changed,
    task_owner,
    subtask_userid,
    DT.hash
FROM Tasks
LEFT JOIN (
    SELECT * FROM delete_task_info
) AS DT ON DT.task_id = Tasks.task_id
WHERE (task_id, task_changed) IN (
    SELECT task_id, task_changed FROM delete_task_info
)
"""

    get_delete_task_message = """
SELECT task_message
FROM TaskStates
WHERE task_id = {task_id} AND task_changed = '{task_changed}'
"""

    get_srcpkg_hash_for_branch_on_date = """
SELECT
    pkg_hash,
    pkg_version,
    pkg_release
FROM Packages
WHERE pkg_hash IN
(
    SELECT pkg_hash
    FROM PackageSet
    WHERE pkg_hash IN (
        SELECT pkg_hash
        FROM Packages
        WHERE pkg_name = '{name}' AND pkg_sourcepackage = 1
    ) AND pkgset_uuid IN (
        SELECT pkgset_uuid
        FROM PackageSetName
        WHERE pkgset_nodename = 'srpm' AND pkgset_ruuid IN (
            SELECT argMax(pkgset_uuid, pkgset_date)
            FROM PackageSetName
            WHERE pkgset_nodename = '{branch}'
                AND toDate(pkgset_date) <= (toDate('{task_changed}') - 1)
        )
    )
)
"""

    get_binpkg_hash_for_branch_on_date = """
SELECT
    pkg_hash,
    pkg_version,
    pkg_release
FROM Packages
WHERE pkg_hash IN (
    SELECT pkg_hash
    FROM PackageSet
    WHERE pkg_hash IN (
        SELECT pkg_hash
        FROM Packages
        WHERE pkg_name = '{name}'
            AND pkg_arch = '{arch}'
            AND pkg_sourcepackage = 0
    ) AND pkgset_uuid IN (
        SELECT pkgset_uuid
        FROM PackageSetName
        WHERE pkgset_depth = 2 AND pkgset_ruuid IN (
            SELECT argMax(pkgset_uuid, pkgset_date)
            FROM PackageSetName
            WHERE pkgset_nodename = '{branch}'
                AND toDate(pkgset_date) <= (toDate('{task_changed}') - 1)
        )
    )
)
"""

    preselect_last_build_task_by_src = """
pkg_name = '{name}'
"""

    preselect_last_build_task_by_bin = """
pkg_hash IN
(
    SELECT pkg_srcrpm_hash
    FROM Packages
    WHERE pkg_name = '{name}'
        AND pkg_arch = '{arch}'
        AND pkg_sourcepackage = 0
)
"""

    get_last_build_task_by_pkg = """
WITH
src_pkg_hashes AS
(
    SELECT
        pkg_hash,
        pkg_version,
        pkg_release
    FROM Packages
    WHERE {preselect} AND pkg_sourcepackage = 1
)
SELECT DISTINCT
    task_id,
    titer_srcrpm_hash,
    PI.pkg_version,
    PI.pkg_release
FROM TaskIterations
LEFT JOIN
(
    SELECT
        pkg_hash,
        pkg_version,
        pkg_release
    FROM src_pkg_hashes
) AS PI ON PI.pkg_hash = titer_srcrpm_hash
WHERE titer_srcrpm_hash IN
    (
        SELECT pkg_hash FROM src_pkg_hashes
    )
    AND (task_id, subtask_id) IN
    (
        SELECT
            task_id, subtask_id
        FROM Tasks
        WHERE task_repo = '{branch}'
            AND subtask_deleted = 0
            AND task_id IN
            (
                SELECT task_id
                FROM TaskStates
                WHERE task_state = 'DONE'
            )
    )
    AND task_changed < '{task_changed}'
ORDER BY task_changed DESC LIMIT 1
"""

    get_last_packages_with_cve_fixes = """
WITH
changelog_with_cve AS
(
    SELECT DISTINCT
        chlog_hash,
        chlog_text
    FROM Changelog
    WHERE match(chlog_text, 'CVE-\d{{4}}-(\d{{7}}|\d{{6}}|\d{{5}}|\d{{4}})')
),
(
    SELECT groupUniqArray(chlog_hash)
    FROM changelog_with_cve
) AS changelog_hashes
SELECT DISTINCT
    pkg_hash,
    pkg_name,
    pkg_version,
    pkg_release,
    pkg_buildtime,
    pkg_summary,
    pkg_changelog.date[1],
    CHLG.chlog_text
FROM Packages
LEFT JOIN
(
    SELECT * FROM changelog_with_cve
) AS CHLG ON CHLG.chlog_hash = (pkg_changelog.hash[1])
WHERE pkg_hash IN
(
    SELECT pkg_hash
    FROM static_last_packages
    WHERE pkgset_name = '{branch}'
        AND pkg_sourcepackage = 1
)
    AND has(changelog_hashes, pkg_changelog.hash[1])
ORDER BY pkg_buildtime DESC
"""

    get_build_task_by_hash = """
SELECT
    task_id,
    subtask_id,
    subtask_arch,
    titer_srcrpm_hash,
    titer_pkgs_hash
FROM TaskIterations
WHERE (task_id, task_changed) IN
(
    SELECT
    argMax(task_id, task_changed),
    max(task_changed)
    FROM TaskIterations
    WHERE titer_srcrpm_hash = {pkghash} AND task_id IN
    (
        SELECT task_id
        FROM TaskStates
        WHERE task_state = 'DONE'
    )
)
    AND titer_srcrpm_hash = {pkghash}
    AND
    (
        SELECT count(task_id)
        FROM Tasks
        WHERE task_repo = '{branch}'
    ) != 0
"""

    get_build_task_by_bin_hash = """
SELECT
    task_id,
    subtask_id,
    subtask_arch,
    titer_srcrpm_hash,
    titer_pkgs_hash
FROM TaskIterations
WHERE (task_id, task_changed) IN (
    SELECT
        argMax(task_id, task_changed),
        max(task_changed)
    FROM TaskIterations
    WHERE has(titer_pkgs_hash, {pkghash}) AND (task_id IN (
        SELECT task_id
        FROM TaskStates
        WHERE task_state = 'DONE'
    ))
)
    AND has(titer_pkgs_hash, {pkghash})
    AND task_id IN (
        SELECT task_id
        FROM Tasks
        WHERE task_repo = '{branch}'
    )
"""

    get_pkgs_filename_by_hshs = """
SELECT
    pkg_hash,
    pkg_filename,
    pkg_arch,
    pkg_filesize
FROM Packages
WHERE pkg_hash IN {hshs}
"""

    get_arepo_pkgs_by_task = """
SELECT
    pkg_hash,
    pkg_filename,
    pkg_arch,
    pkg_filesize
FROM Packages
WHERE pkg_hash IN (
    SELECT pkgh_mmh
    FROM PackageHash
    WHERE pkgh_sha256 IN (
        SELECT tplan_sha256
        FROM TaskPlanPkgHash
        WHERE tplan_action = 'add'
            AND tplan_hash IN (
                SELECT tplan_hash
                FROM task_plan_hashes
                WHERE task_id = {taskid}
                    AND tplan_arch = 'x86_64-i586'
            )
    )
)
"""

    get_src_and_binary_pkgs = """
SELECT DISTINCT
    pkg_hash,
    pkg_filename,
    pkg_arch,
    pkg_filesize
FROM last_packages
WHERE pkg_srcrpm_hash = {pkghash} AND pkgset_name = '{branch}'
"""

    get_bin_pkg_from_last = """
SELECT DISTINCT
    pkg_hash,
    pkg_filename,
    pkg_arch,
    pkg_filesize
FROM last_packages
WHERE pkg_hash = {pkghash}
    AND pkgset_name = '{branch}'
    AND pkg_arch = '{arch}'
"""

    get_pkgs_md5_by_hshs = """
SELECT
    pkgh_mmh,
    pkgh_md5
FROM PackageHash_view
WHERE pkgh_mmh IN {hshs}
"""

    get_pkg_versions_by_hash = """
SELECT DISTINCT
    pkgset_name,
    pkg_version,
    pkg_release,
    toString(pkg_hash)
FROM static_last_packages
WHERE pkg_name = (
    SELECT DISTINCT pkg_name
    FROM static_last_packages
    WHERE pkg_hash = {pkghash}
        AND pkg_sourcepackage = 1
)
    AND pkg_sourcepackage = 1
"""

    get_bin_pkg_versions_by_hash = """
WITH
(
    SELECT DISTINCT pkg_name
    FROM static_last_packages
    WHERE pkg_hash = {pkghash}
        AND pkg_sourcepackage = 0
) AS pkgname
SELECT DISTINCT
    pkgset_name,
    pkg_version,
    pkg_release,
    toString(pkg_hash),
    PA.pkg_arch
FROM static_last_packages
INNER JOIN
(
    SELECT pkg_hash, pkg_arch
    FROM Packages
    WHERE pkg_sourcepackage = 0
        AND pkg_name = pkgname
        AND pkg_arch = '{arch}'
) AS PA ON PA.pkg_hash  = static_last_packages.pkg_hash
WHERE pkg_name = pkgname
    AND pkg_sourcepackage = 0
"""

    get_pkgs_binary_list = """
SELECT DISTINCT
    pkg_hash,
    pkg_name,
    pkg_version,
    pkg_release,
    pkg_arch
FROM last_packages
WHERE pkgset_name = '{branch}'
    AND pkg_name = '{name}'
    AND pkg_sourcepackage = 0
"""

    get_pkg_binary_list_versions = """
SELECT DISTINCT
    pkgset_name,
    pkg_version,
    pkg_release
FROM static_last_packages
WHERE pkg_name = '{name}'
    AND pkg_sourcepackage = 0
GROUP BY
    pkgset_name,
    pkg_version,
    pkg_release
"""

    get_bin_pkg_scripts = """
SELECT
    pkg_postin,
    pkg_postun,
    pkg_prein,
    pkg_preun
FROM Packages
WHERE pkg_hash = {pkghash}
    AND pkg_sourcepackage = 0
"""

    get_pkgs_name_and_arch = """
    SELECT
        pkg_name,
        pkg_arch
    FROM Packages
    WHERE pkg_hash = {pkghash}
"""

    get_bin_pkg_log = """
    SELECT
        task_id,
        subtask_id,
        subtask_arch,
        titer_buildlog_hash
    FROM TaskIterations
    WHERE has(titer_pkgs_hash, {pkghash})
        AND (task_id, task_changed) IN
        (
            SELECT
                task_id,
                task_changed
            FROM TaskStates
            WHERE task_state = 'DONE'
        )
"""

    get_package_nvr_by_hash = """
SELECT DISTINCT
    pkg_hash,
    pkg_name,
    pkg_version,
    pkg_release,
    pkg_sourcepackage
FROM Packages
WHERE pkg_hash = {pkghash}
"""


sql = SQL()
