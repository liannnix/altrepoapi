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
    get_vuln_info_by_ids = """
SELECT
    vuln_hash,
    vuln_id,
    vuln_summary,
    vuln_score,
    vuln_severity,
    vuln_url,
    vuln_modified_date,
    vuln_published_date,
    {json_field},
    vuln_references.type,
    vuln_references.link
FROM Vulnerabilities
WHERE (vuln_id, vuln_hash) IN (
    SELECT
        vuln_id,
        argMax(vuln_hash, ts)
    FROM Vulnerabilities
    WHERE vuln_id IN {tmp_table}
    GROUP BY vuln_id
)
"""

    get_cves_cpe_matching = """
SELECT
    vuln_id,
    groupUniqArray(
        tuple(
            cpm_cpe,
            cpm_version_start,
            cpm_version_end,
            cpm_version_start_excluded,
            cpm_version_end_excluded
        )
    )
FROM CpeMatch
WHERE vuln_hash IN {tmp_table}
    AND (
        cpm_cpe LIKE 'cpe:2.3:a:%'
        OR cpm_cpe LIKE 'cpe:2.3:o:linux:linux_kernel:%'
        OR cpm_cpe LIKE 'cpe:2.3:o:linux:kernel:%'
    )
GROUP BY vuln_id
"""

    get_cves_cpems_by_cpe = """
SELECT
    vuln_id,
    groupUniqArray(
        tuple(
            cpm_cpe,
            cpm_version_start,
            cpm_version_end,
            cpm_version_start_excluded,
            cpm_version_end_excluded
        )
    )
FROM CpeMatch
WHERE cpm_cpe IN {tmp_table}
    AND (vuln_id, vuln_hash) IN (
        SELECT
            vuln_id,
            argMax(vuln_hash, ts)
        FROM Vulnerabilities
        GROUP BY vuln_id
    )
GROUP BY vuln_id
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
    cpe
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
{pkg_names_clause}
"""

    get_branch_src_packages = """
SELECT DISTINCT pkg_name
FROM static_last_packages
WHERE pkg_sourcepackage = 1
    AND pkgset_name = '{branch}'
"""

    get_packages_versions = """
SELECT DISTINCT
    toString(pkg_hash),
    pkg_name,
    pkg_version,
    pkg_release,
    pkgset_name
FROM static_last_packages
WHERE pkg_sourcepackage = 1
    AND pkg_name IN (
        SELECT * FROM {tmp_table}
    )
    AND pkgset_name IN {branches}
"""

    get_packages_versions_for_show_branches = """
SELECT DISTINCT
    toString(pkg_hash),
    pkg_name,
    pkg_version,
    pkg_release,
    pkgset_name
FROM static_last_packages
WHERE pkg_sourcepackage = 1
    AND pkg_name IN (
        SELECT * FROM {tmp_table}
    )
    AND pkgset_name IN (
        SELECT pkgset_name
        FROM (
            SELECT
                pkgset_name,
                argMax(rs_show, ts) AS show
            FROM RepositoryStatus
            GROUP BY pkgset_name
        )
        WHERE show = 1
    )
"""

    get_erratas = """
SELECT
    errata_id,
    eh_references.type,
    eh_references.link,
    pkgset_name,
    task_id,
    subtask_id,
    task_state,
    toString(pkg_hash),
    pkg_name,
    pkg_version,
    pkg_release,
    eh_updated
FROM ErrataHistory
WHERE (errata_id, eh_updated) IN (
    SELECT
        eid, updated
    FROM (
        SELECT
            errata_id_noversion,
            argMax(errata_id, eh_updated) AS eid,
            max(eh_updated) AS updated
        FROM ErrataHistory
        WHERE eh_type IN ('branch', 'task')
        {where_clause}
        GROUP BY errata_id_noversion
    )
    WHERE eid NOT IN (
        SELECT errata_id FROM last_discarded_erratas
    )
)
ORDER BY eh_updated DESC
"""

    get_last_tasks_state = """
WITH
last_task_states AS (
    SELECT
        task_id,
        argMax(task_state, task_changed) AS state,
        max(task_changed) AS changed
    FROM TaskStates
    WHERE task_id IN {tmp_table}
    GROUP BY task_id
),
last_task_subtasks AS (
    SELECT
        task_id,
        groupUniqArray(subtask_id) AS subtasks
    FROM Tasks
    WHERE (task_id, task_changed) IN (
        SELECT task_id, changed FROM last_task_states
    )
    GROUP BY task_id
    HAVING subtask_deleted = 0
)
SELECT
    task_id,
    state,
    changed,
    subtasks
FROM last_task_states
LEFT JOIN last_task_subtasks AS LTS USING task_id
"""

    get_maintainer_pkg = """
SELECT DISTINCT pkg_name
FROM last_packages
WHERE pkg_sourcepackage = 1
    AND pkgset_name = '{branch}'
    AND pkg_packager_email LIKE '{maintainer_nickname}@%'
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
SELECT DISTINCT pkg_name
FROM static_last_packages
WHERE pkg_sourcepackage = 1
      AND pkgset_name = '{branch}'
      AND pkg_name IN (
        SELECT acl_for
        FROM last_acl_stage1
        WHERE acl_branch = 'sisyphus'
          AND (has(acl_list, '{maintainer_nickname}')
          OR hasAny(acl_list, acl_group))
    )
"""

    get_maintainer_pkg_by_nick_leader_acl = """
SELECT DISTINCT pkg_name
FROM static_last_packages
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
"""

    get_maintainer_pkg_by_nick_acl = """
SELECT DISTINCT pkg_name
FROM static_last_packages
WHERE pkg_sourcepackage = 1
      AND pkgset_name = '{branch}'
      AND pkg_name IN (
        SELECT acl_for
        FROM last_acl_stage1
        WHERE acl_branch = 'sisyphus'
          AND has(acl_list, '{maintainer_nickname}')
    )
"""

    get_maintainer_pkg_by_nick_leader_and_group_acl = """
SELECT DISTINCT pkg_name
FROM static_last_packages
WHERE pkg_sourcepackage = 1
      AND pkgset_name = '{branch}'
      AND pkg_name IN (
        SELECT pkgname
        FROM last_acl_with_groups
        WHERE acl_user = '{maintainer_nickname}'
            AND acl_branch = 'sisyphus'
            AND order_u = 1
)
"""

    check_task = """
SELECT count(task_id)
FROM TaskStates
WHERE task_id = {id}
"""

    get_task_cve_from_erratas = """
WITH task_subtasks AS (
    SELECT DISTINCT task_id, subtask_id
    FROM Tasks
    WHERE (task_id, task_changed) IN (
        SELECT task_id,
            max(task_changed) AS changed
        FROM TaskStates
        WHERE task_id = {task_id}
        GROUP BY task_id
    )
    AND subtask_deleted = 0
)
SELECT * FROM (
    SELECT
        argMax(pkg_hash, ts),
        subtask_id,
        argMax(pkg_name, ts),
        argMax(pkg_version, ts),
        argMax(pkg_release, ts),
        argMax(pkgset_name, ts),
        argMax(errata_id, ts) AS eid,
        argMax(eh_references.link, ts),
        argMax(eh_references.type, ts)
    FROM ErrataHistory
    WHERE eh_type = 'task'
        AND (task_id, subtask_id) IN (SELECT * FROM task_subtasks)
    GROUP BY subtask_id
    ORDER BY subtask_id
)
WHERE eid NOT IN (
    SELECT errata_id FROM last_discarded_erratas
)
"""

    get_done_tasks_by_packages = """
SELECT DISTINCT
    task_id,
    pkgset_name,
    pkg_name
FROM BranchPackageHistory
WHERE pkgset_name in {branches}
    AND pkg_name IN {tmp_table}
    AND pkg_sourcepackage = 1
    AND tplan_action = 'add'
ORDER BY task_changed DESC
"""

    get_done_tasks_by_packages_and_branches = """
SELECT DISTINCT
    task_id,
    pkgset_name,
    pkg_name
FROM BranchPackageHistory
WHERE (pkg_name, pkgset_name) IN (
        SELECT pkg_name, pkgset_name FROM {tmp_table}
    )
    AND pkg_sourcepackage = 1
    AND tplan_action = 'add'
ORDER BY task_changed DESC
"""

    get_done_tasks_history = """
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
-- ORDER BY task_changed DESC
"""


sql = SQL()
