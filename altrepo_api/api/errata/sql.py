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
    get_bin_pkgs_by_src_hshs = """
SELECT DISTINCT
    pkg_hash,
    pkg_name,
    pkg_epoch,
    pkg_version,
    pkg_release,
    pkg_srcrpm_hash
FROM Packages
WHERE pkg_srcrpm_hash IN
(
    SELECT pkg_hash FROM {tmp_table}
)
    AND pkg_sourcepackage = 0
    AND pkg_name NOT LIKE '%%-debuginfo'
"""

    get_bugzilla_summary_by_ids = """
SELECT
    bz_id,
    argMax(bz_summary, ts)
FROM Bugzilla
WHERE bz_id IN (
    SELECT bz_id FROM {tmp_table}
)
GROUP BY bz_id
"""

    get_errata_history_by_branch_tasks = """
WITH
done_subtasks AS (
    SELECT DISTINCT
        task_id,
        subtask_id
    FROM Tasks
    WHERE task_repo = '{branch}'
        AND task_id IN (
            SELECT task_id FROM TaskStates WHERE task_state = 'DONE'
        )
        AND subtask_deleted = 0
)
SELECT DISTINCT *
FROM ErrataHistory
WHERE eh_type = 'task'
    AND (task_id, subtask_id) IN done_subtasks
    AND task_state = 'DONE'
    {pkg_name_clause}
ORDER BY task_changed
"""

    get_vulns_info_by_ids = """
SELECT
    vuln_id,
    vuln_summary,
    vuln_score,
    vuln_severity,
    vuln_url,
    vuln_modified_date,
    vuln_published_date,
    vuln_json
FROM Vulnerabilities
WHERE (vuln_id, vuln_hash) IN (
    SELECT
        vuln_id,
        argMax(vuln_hash, ts)
    FROM Vulnerabilities
    WHERE vuln_id IN (SELECT vuln_id FROM {tmp_table})
    GROUP BY vuln_id
)
"""

    get_bdus_info_by_cve_ids = """
SELECT
    vuln_id,
    vuln_summary,
    vuln_score,
    vuln_severity,
    vuln_url,
    vuln_modified_date,
    vuln_published_date,
    vuln_json,
    vuln_references.link
FROM Vulnerabilities
WHERE (vuln_id, vuln_hash) IN (
    SELECT
        vuln_id,
        argMax(vuln_hash, ts)
    FROM Vulnerabilities
    WHERE vuln_type = 'BDU'
        AND hasAny(
            vuln_references.link,
            (
                SELECT groupUniqArray(vuln_id) FROM {tmp_table}
            )
        )
    GROUP BY vuln_id
)
"""

    get_errata_history_by_id = """
SELECT
    eh_hash,
    eh_type,
    eh_source,
    arrayZip(eh_references.type, eh_references.link),
    errata_id,
    pkg_hash,
    pkg_name,
    pkg_version,
    pkg_release,
    pkgset_name,
    pkgset_date,
    task_id,
    subtask_id,
    task_state,
    task_changed
FROM ErrataHistory
WHERE errata_id = '{errata_id}'
"""

    get_errata_history_by_ids = """
SELECT
    eh_hash,
    eh_type,
    eh_source,
    arrayZip(eh_references.type, eh_references.link),
    errata_id,
    pkg_hash,
    pkg_name,
    pkg_version,
    pkg_release,
    pkgset_name,
    pkgset_date,
    task_id,
    subtask_id,
    task_state,
    task_changed
FROM ErrataHistory
WHERE errata_id IN (
    SELECT errata_id FROM {tmp_table}
)
"""

    get_vulns_by_ids = """
SELECT
    vuln_id,
    vuln_hash,
    vuln_type,
    vuln_summary,
    vuln_score,
    vuln_severity,
    vuln_url,
    arrayZip(vuln_references.type, vuln_references.link),
    vuln_modified_date,
    vuln_published_date,
    vuln_json
FROM Vulnerabilities
WHERE vuln_id IN (
    SELECT vuln_id FROM {tmp_table}
)
"""

    get_bugs_by_ids = """
SELECT *
FROM Bugzilla
WHERE bz_id IN (
    SELECT bz_id FROM {tmp_table}
)
"""

    search_errata = """
SELECT
    eh_hash,
    eh_type,
    eh_source,
    arrayZip(eh_references.type, eh_references.link),
    errata_id,
    pkg_hash,
    pkg_name,
    pkg_version,
    pkg_release,
    pkgset_name,
    pkgset_date,
    task_id,
    subtask_id,
    task_state,
    task_changed
FROM ErrataHistory
{cond}
ORDER BY ts DESC
"""


sql = SQL()
