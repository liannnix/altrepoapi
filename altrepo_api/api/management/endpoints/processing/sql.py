# ALTRepo API
# Copyright (C) 2021-2024  BaseALT Ltd

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
    get_erratas_by_pkgs_names = """
SELECT EI.*, DE.discarded_id as discarded_id
FROM (
    SELECT *
    FROM ErrataHistory
    WHERE errata_id IN (
        SELECT eid
        FROM (
            SELECT
                errata_id_noversion,
                argMax(errata_id, errata_id_version) AS eid
            FROM ErrataHistory
            WHERE eh_type = 'task' AND task_state = 'DONE'
                AND pkgset_name IN {branches}
                AND pkg_name IN {tmp_table}
            GROUP BY errata_id_noversion
        )
    )
) AS EI
LEFT JOIN (
    SELECT errata_id AS discarded_id
    FROM last_discarded_erratas
) AS DE ON errata_id = DE.discarded_id
"""

    get_erratas_by_cve_ids = """
WITH
(
    SELECT groupUniqArray(cve_id) FROM {tmp_table}
) AS cve_ids
SELECT EI.*, DE.discarded_id as discarded_id
FROM (
    SELECT *
    FROM ErrataHistory
    WHERE errata_id IN (
        SELECT eid
        FROM (
            SELECT
                errata_id_noversion,
                argMax(errata_id, errata_id_version) AS eid
            FROM ErrataHistory
            WHERE eh_type = 'task' AND task_state = 'DONE'
                AND pkgset_name IN {branches}
                AND hasAny(eh_references.link, cve_ids)
            GROUP BY errata_id_noversion
        )
    )
) AS EI
LEFT JOIN (
    SELECT errata_id AS discarded_id
    FROM last_discarded_erratas
) AS DE ON errata_id = DE.discarded_id
"""

    get_packages_versions = """
SELECT DISTINCT
    pkg_hash,
    pkg_name,
    pkg_version,
    pkg_release,
    pkgset_name
FROM static_last_packages
WHERE pkg_hash IN {tmp_table}
    AND pkg_sourcepackage = 1
"""

    get_packages_changelogs = """
WITH package_changelog AS
    (
        SELECT
            pkg_hash,
            pkg_changelog.date AS date,
            pkg_changelog.name as name,
            pkg_changelog.evr AS evr,
            pkg_changelog.hash AS hash
        FROM Packages
ARRAY JOIN pkg_changelog
        PREWHERE pkg_hash IN (SELECT * FROM {tmp_table})
    )
SELECT DISTINCT
    pkg_hash,
    date,
    name,
    evr,
    Chg.chlog_text as text
FROM package_changelog
LEFT JOIN
(
    SELECT DISTINCT
        chlog_hash AS hash,
        chlog_text
    FROM Changelog
    WHERE chlog_hash IN (
        SELECT hash
        FROM package_changelog
    )
) AS Chg ON Chg.hash = package_changelog.hash
"""

    get_done_tasks = """
WITH
tasks_history AS (
    SELECT DISTINCT
        task_id,
        task_changed,
        pkgset_name,
        pkg_hash,
        pkg_name,
        pkg_version,
        pkg_release
    FROM BranchPackageHistory
    {where_clause}
    ORDER BY task_changed DESC
)
SELECT DISTINCT
    task_id,
    subtask_id,
    pkgset_name,
    pkg_hash,
    pkg_name,
    pkg_version,
    pkg_release,
    task_changed
FROM tasks_history
LEFT JOIN (
    SELECT
        task_id,
        subtask_id,
        titer_srcrpm_hash AS pkg_hash
    FROM TaskIterations
    WHERE (task_id, task_changed, pkg_hash) IN (
        SELECT task_id, task_changed, pkg_hash FROM tasks_history
    )
) AS subtasks USING (task_id, pkg_hash)
"""

    get_done_tasks_by_packages_clause = """
WHERE pkgset_name in {branches}
    AND pkg_name IN {tmp_table}
    AND pkg_sourcepackage = 1
    AND tplan_action = 'add'
"""

    get_done_tasks_by_nevr_cluse = """
WHERE pkgset_name in {branches}
    AND pkg_name = '{name}'
    AND pkg_epoch = {epoch}
    AND pkg_version = '{version}'
    AND pkg_release = '{release}'
    AND pkg_sourcepackage = 1
    AND tplan_action = 'add'
"""

    get_cve_versions_matches = """
SELECT
    vuln_id,
    vuln_hash,
    cpe_hash,
    cpm_version_hash,
    cpm_cpe,
    cpm_version_start,
    cpm_version_end,
    cpm_version_start_excluded,
    cpm_version_end_excluded
FROM CpeMatch
WHERE (vuln_hash, cpe_hash, cpm_version_hash) IN {tmp_table}
"""

    get_bdus_by_cves = """
SELECT
    vuln_id,
    vuln_references.type,
    vuln_references.link
FROM Vulnerabilities
WHERE (vuln_id, vuln_hash) IN (
    SELECT
        vuln_id,
        argMax(vuln_hash, ts)
    FROM Vulnerabilities
    WHERE vuln_id IN (
        SELECT vuln_id
        FROM Vulnerabilities
        WHERE arrayExists(x -> (x IN {tmp_table}), `vuln_references.link`)
    )
    GROUP BY vuln_id
)
"""

    get_affected_erratas_by_transaction_id = """
SELECT DISTINCT
    ec_id,
    errata_id
FROM ErrataChangeHistory
WHERE transaction_id = '{transaction_id}'
"""

    delete_errata_history_records = """
DLETE FROM ErrataHistory WHERE errata_id in {tmp_table}
"""

    delete_errata_change_history_records = """
DLETE FROM ErrataChangeHistory WHERE transaction_id = '{transaction_id}'
"""

    delete_pnc_change_history_records = """
DLETE FROM PncChangeHistory WHERE transaction_id = '{transaction_id}'
"""


sql = SQL()
