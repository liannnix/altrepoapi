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
SELECT DISTINCT * EXCEPT ts
FROM ErrataHistory
WHERE eh_type = 'task' AND errata_id IN (
    SELECT eid
    FROM (
        SELECT
            errata_id_noversion,
            argMax(errata_id, eh_updated) AS eid
        FROM ErrataHistory
        WHERE task_state = 'DONE' AND pkgset_name = '{branch}'
        GROUP BY errata_id_noversion
    )
)
{pkg_name_clause}
ORDER BY eh_updated
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

    get_vulns_by_ids = """
SELECT
    vuln_id,
    vuln_type,
    vuln_hash,
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
SELECT
    bz_id,
    bz_summary
FROM Bugzilla
WHERE bz_id IN (
    SELECT bz_id FROM {tmp_table}
)
"""

    search_errata_where_clause = """
WHERE (task_id, subtask_id) IN (
    SELECT DISTINCT
        task_id,
        subtask_id
    FROM Tasks
    WHERE task_id IN (
            SELECT task_id FROM TaskStates WHERE task_state = 'DONE'
        )
        AND subtask_deleted = 0
    UNION ALL
    SELECT 0 AS task_id, 0 AS subtask_id
)
"""

    errata_by_ids_where_clause = """
WHERE errata_id IN (
    SELECT errata_id FROM {tmp_table}
)
"""

    search_valid_errata = """
SELECT
    errata_id_noversion,
    argMax(
        tuple(
            errata_id,
            eh_type,
            eh_source,
            eh_created,
            eh_updated,
            pkg_hash,
            pkg_name,
            pkg_version,
            pkg_release,
            pkgset_name,
            task_id,
            subtask_id,
            task_state,
            arrayZip(eh_references.type, eh_references.link)
        ),
        eh_updated
    ),
    max(eh_updated) AS max_ts
FROM ErrataHistory
{where_clause}
GROUP BY errata_id_noversion
ORDER BY max_ts DESC
"""

    get_valid_errata_ids = """
SELECT DISTINCT eid
FROM (
    SELECT
        errata_id_noversion,
        argMax(errata_id, eh_updated) AS eid,
        max(eh_updated) AS updated
    FROM ErrataHistory
    WHERE task_state = 'DONE' OR (task_id = 0 AND subtask_id = 0)
    GROUP BY errata_id_noversion
    ORDER BY updated DESC
)
"""

    get_errata_branches = """
SELECT DISTINCT pkgset_name
FROM ErrataHistory
WHERE pkgset_name != 'icarus'
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

    find_erratas = """
WITH errata_tasks AS (
    SELECT
        errata_id,
        argMax(eh_type, ts)  AS type,
        argMax(task_id, ts) AS tsk_id,
        argMax(pkgset_name, ts) AS branch,
        groupUniqArray((pkg_hash, pkg_name, pkg_version, pkg_release)) as packages,
        argMax(eh_references.link, ts) AS refs_links,
        argMax(eh_references.type, ts) AS refs_types,
        max(eh_updated) AS changed
    FROM ErrataHistory
    WHERE eh_type = 'task' AND errata_id IN (
        SELECT eid
        FROM (
            SELECT
                errata_id_noversion,
                argMax(errata_id, eh_updated) AS eid
            FROM ErrataHistory
            WHERE task_state = 'DONE'
            {branch}
            GROUP BY errata_id_noversion
        )
    )
    GROUP BY errata_id
),
errata_branches AS (
    SELECT
        errata_id,
        argMax(eh_type, ts)  AS type,
        argMax(task_id, ts) AS tsk_id,
        argMax(pkgset_name, ts) AS branch,
        groupUniqArray((pkg_hash, pkg_name, pkg_version, pkg_release)) as packages,
        argMax(eh_references.link, ts) AS refs_links,
        argMax(eh_references.type, ts) AS refs_types,
        max(eh_updated) AS changed
    FROM ErrataHistory
    WHERE eh_type = 'branch'
    {branch}
    GROUP BY errata_id
),
errata_bulletin AS (
    SELECT
        errata_id,
        argMax(eh_type, ts)  AS type,
        argMax(task_id, ts) AS tsk_id,
        argMax(pkgset_name, ts) AS branch,
        groupUniqArray((pkg_hash, pkg_name, pkg_version, pkg_release)) as packages,
        arrayJoin(eh_references.link) AS ref_link,
        argMax(eh_references.type, ts) AS refs_types,
        max(eh_updated) AS changed
    FROM ErrataHistory
    WHERE eh_type == 'bulletin'
    {branch}
    GROUP BY errata_id, eh_type, ref_link
)
SELECT * FROM (
    SELECT * FROM errata_tasks
    UNION ALL
    SELECT * FROM errata_branches
    UNION ALL
    SELECT errata_id,
           type,
           tsk_id,
           branch,
           if(type='bulletin', groupUniqArray((PKGS.pkghash, PKGS.pkg_name, PKGS.pkg_version, PKGS.pkg_release)), packages) AS pkgs,
           groupUniqArray(ref_link) AS ref_links,
           refs_types,
           changed
           FROM errata_bulletin
           LEFT JOIN (
                SELECT errata_id,
                       argMax(pkg_hash, ts) AS pkghash,
                       argMax(pkg_name, ts) AS pkg_name,
                       argMax(pkg_version, ts) AS pkg_version,
                       argMax(pkg_release, ts) AS pkg_release
                FROM ErrataHistory
                GROUP BY errata_id
           ) AS PKGS ON PKGS.errata_id = ref_link
           GROUP BY errata_id,
                  type,
                  tsk_id,
                  branch,
                  packages,
                  refs_types,
                  changed
)
{where_clause}
ORDER BY changed DESC
"""


sql = SQL()
