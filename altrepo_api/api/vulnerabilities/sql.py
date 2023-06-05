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
    CPE_BRANCH_MAP = {
        # P9
        "p9": "alt_p9",
        "c9f1": "alt_p9",
        "c9f2": "alt_p9",
        "p9_e2k": "alt_p9",
        "p9_mipsel": "alt_p9",
        # P10
        "p10": "alt_p10",
        "c10f1": "alt_p10",
        "c10f2": "alt_p10",
        "p10_e2k": "alt_p10",
        # Sisyphus
        "sisyphus": "altsisyphus",
        "sisyphus_e2k": "altsisyphus",
        "sisyphus_mipsel": "altsisyphus",
        "sisyphus_riscv64": "altsisyphus",
    }

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
    vuln_json,
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

    get_packages_and_cpes = """
WITH
repology_names AS (
    SELECT
        alt_name,
        repology_name
    FROM (
        SELECT
            pkg_name AS alt_name,
            argMax(pnc_result, ts) AS repology_name,
            argMax(pnc_state, ts) AS state
        FROM PackagesNameConversion
        WHERE pnc_type IN {cpe_branches}
        GROUP BY alt_name
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

    get_errata_by_packages = """
SELECT
    errata_id,
    argMax(
        tuple(
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
            pkg_release
        ),
        ts
    ),
    max(ts) AS max_ts
FROM ErrataHistory
WHERE (
    eh_type = 'branch' OR (
        eh_type = 'task'
            AND (task_id, subtask_id) IN (
                SELECT DISTINCT
                    task_id,
                    subtask_id
                FROM Tasks
                WHERE (task_id, task_changed) IN (
                    SELECT task_id, changed FROM (
                        SELECT
                            task_id,
                            max(task_changed) AS changed,
                            argMax(task_state, task_changed) AS state
                        FROM TaskStates
                        GROUP BY task_id
                    )  WHERE state IN ('EPERM', 'TESTED', 'DONE')
                )
                    AND subtask_deleted = 0
            )
        )
    )
    {branch_clause}
    AND pkg_name IN (SELECT pkg_name FROM {tmp_table})
    AND has(eh_references.type, 'vuln')
GROUP BY errata_id
ORDER BY max_ts DESC
"""

    get_errata_by_cves = """
SELECT
    errata_id,
    argMax(
        tuple(
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
            pkg_release
        ),
        ts
    ),
    max(ts) AS max_ts
FROM ErrataHistory
WHERE eh_type IN ('branch', 'task')
    {branch_clause}
    AND hasAny(eh_references.link, {cve_ids})
GROUP BY errata_id
ORDER BY max_ts DESC
"""

    get_last_tasks_state = """
SELECT
    task_id,
    argMax(task_state, task_changed) AS state
FROM TaskStates
WHERE task_id IN {tmp_table}
GROUP BY task_id
"""


sql = SQL()
