# ALTRepo API
# Copyright (C) 2021-2025  BaseALT Ltd

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

    get_packages_and_cpes = """
WITH
repology_names AS (
    SELECT
        alt_name,
        repology_name
    FROM (
        SELECT
            pkg_name AS alt_name,
            pnc_result AS repology_name,
            argMax(pnc_state, ts) AS state
        FROM PackagesNameConversion
        WHERE pnc_type IN {cpe_branches}
        GROUP BY pkg_name, pnc_result
    ) WHERE state = 'active'
)
SELECT
    alt_name AS pkg_name,
    arraySort(groupUniqArray(cpe))
FROM (
    SELECT
        cpe_pkg_name,
        cpe
    FROM (
        SELECT
            pkg_name AS cpe_pkg_name,
            argMax(pnc_result, ts) AS cpe,
            argMax(pnc_state, ts) AS state
        FROM PackagesNameConversion
        WHERE pnc_type = 'cpe'
        GROUP BY pkg_name, pnc_result
    ) WHERE state = 'active'
) AS CPE
INNER JOIN repology_names AS EN ON EN.repology_name = cpe_pkg_name
GROUP BY alt_name
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

    get_packages_descriptions_from_date = """
WITH
pkgset_roots AS (
    SELECT pkgset_uuid
    FROM PackageSetName
    WHERE pkgset_depth = 0
        AND pkgset_nodename IN {branches}
        AND pkgset_date >= '{from_date}'
),
pkgset_uuids AS (
    SELECT pkgset_uuid
    FROM PackageSetName
    WHERE pkgset_ruuid IN pkgset_roots
        AND (
            (pkgset_depth = 1 AND pkgset_nodename = 'srpm') OR
            (pkgset_depth = 2 AND pkgset_nodename != 'debuginfo')
        )
)
SELECT DISTINCT
    pkg_name,
    pkg_url,
    pkg_summary,
    pkg_description,
    arrayStringConcat(arrayPopBack(arrayPopBack(splitByChar('-', pkg_sourcerpm))), '-') AS src_pkg_name
FROM Packages
WHERE pkg_hash IN (
    SELECT DISTINCT pkg_hash from PackageSet WHERE pkgset_uuid IN pkgset_uuids
)
ORDER BY pkg_name;
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
WHERE task_state = 'DONE'
    AND task_id IN (
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

    get_beehive_errors_by_branch_and_arch = """
WITH
last_bh_updated AS
(
    SELECT
        pkgset_name,
        bh_arch as arch,
        max(bh_updated) AS updated
    FROM BeehiveStatus
    WHERE pkgset_name = '{branch}' AND bh_arch IN {archs}
    GROUP BY
        pkgset_name,
        bh_arch
),
src_packages AS
(
    SELECT
        pkg_hash,
        pkg_epoch
    FROM last_packages
    WHERE pkgset_name = '{branch}' AND pkg_sourcepackage = 1
)
SELECT
    pkgset_name,
    pkg_hash,
    pkg_name,
    Pkg.pkg_epoch,
    pkg_version,
    pkg_release,
    bh_arch,
    bh_updated,
    bh_ftbfs_since
FROM BeehiveStatus
LEFT JOIN
(SELECT pkg_hash, pkg_epoch FROM src_packages) AS Pkg USING (pkg_hash)
WHERE pkgset_name = '{branch}'
    AND bh_status = 'error'
    AND (bh_arch, bh_updated) IN (
        SELECT arch, updated FROM last_bh_updated
    )
    AND pkg_hash IN (
        SELECT pkg_hash FROM src_packages
    )
ORDER BY pkg_name
"""


sql = SQL()
