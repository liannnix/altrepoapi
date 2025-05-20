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
    drop_tmp_table = """
DROP TABLE {tmp_table}
"""

    check_task = """
SELECT count(task_id)
FROM TaskStates
WHERE task_id = {id}
AND task_state IN ['DONE', 'TESTED', 'EPERM']
"""

    supported_branches = """
SELECT pkgset_name
FROM (
    SELECT DISTINCT pkgset_name, argMax(rs_end_date, ts) AS end_date
    FROM RepositoryStatus
    GROUP BY pkgset_name
) AS BR
WHERE BR.end_date > today()
{branch}
"""

    get_all_maintainers = """
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
    WHERE pkg_sourcepackage = 1
    {branch}
    GROUP BY
        pkg_packager,
        packager_nick
)
GROUP BY packager_nick ORDER BY lower(name)
"""

    get_task_list = """
WITH global_search AS (
    SELECT
        task_id,
        SS[1] AS repo,
        SS[2] AS owner,
        SS[4] AS state,
        ts
    FROM (
        SELECT
            task_id,
            arraySlice(
                splitByChar('|', search),
                1,
                4
            ) AS SS,
            ts_ AS ts
        FROM (
            SELECT
                toUInt32(lead) AS task_id,
                argMax(search_string, ts) AS search,
                max(ts) AS ts_
            FROM GlobalSearch
            WHERE type = 'task'
            {where_clause_tasks}
            GROUP BY lead
            ORDER BY max(ts) DESC
        )
        WHERE {state_clause}
        AND task_id IN (
             SELECT task_id FROM (
                 SELECT
                    task_id,
                    subtask_id,
                    argMax(subtask_type, task_changed) AS sub_type,
                    argMax(subtask_srpm, task_changed) AS srpm,
                    argMax(subtask_dir, task_changed) AS dir,
                    argMax(subtask_package, task_changed) AS package,
                    if(has(groupUniqArray(subtask_deleted), 0), 'create', 'delete') AS tp
                FROM Tasks
                GROUP BY task_id, subtask_id
             ) WHERE (sub_type != 'unknown' OR arrayFilter(x -> notEmpty(x), [srpm, package, dir]) != []) AND (tp != 'delete') AND (sub_type != 'delete')
         )
        {where_clause_tasks2}
    )
),
errata_tasks AS (
    SELECT DISTINCT
        errata_id,
        task_id,
        eh_references.link AS refs_links,
        eh_references.type AS refs_types,
        eh_updated AS changed
    FROM ErrataHistory
    WHERE errata_id IN (
        SELECT eid
        FROM (
            SELECT
                errata_id_noversion,
                argMax(errata_id, errata_id_version) AS eid
            FROM ErrataHistory
            WHERE eh_type = 'task' AND task_state IN {state_clause2} AND pkgset_name != 'icarus'
            {branch_errata_clause}
            GROUP BY errata_id_noversion
        )
    ) AND errata_id NOT IN (
        SELECT errata_id FROM last_discarded_erratas
    )
)
SELECT * FROM (
    SELECT
        global_search.*,
        TT.errata_id as errata,
        TT.refs_links,
        TT.refs_types
    FROM global_search
    LEFT JOIN (
        SELECT  * FROM errata_tasks
    ) AS TT ON TT.task_id = global_search.task_id
    {where_clause_errata}
) {where_clause_is_errata}
"""

    # XXX: for 'EPERM' tasks use 'task_changed' from TaskStates table instead of
    # temporary table due to GlobalSearch 'ts' is inconsistent with TaskIterations table
    get_subtasks = """
WITH pkg_hashes AS (
    SELECT task_id,
           subtask_id,
           titer_srcrpm_hash,
           subtask_arch
    FROM TaskIterations
    WHERE (task_id, task_changed) IN (
        SELECT task_id, changed
        FROM {tmp_table}
        WHERE state IN ('DONE', 'TESTED')
        UNION ALL
        SELECT task_id, max(task_changed)
        FROM TaskStates
        WHERE (task_id, task_state) IN (
            SELECT task_id, state
            FROM {tmp_table}
            WHERE state = 'EPERM'
        )
        GROUP BY task_id
    )
        AND titer_srcrpm_hash != 0
),
tasks_info AS (
    SELECT
        task_id,
        subtask_id,
        argMax(subtask_type, ts) AS sub_type,
        argMax(subtask_changed, ts) AS changed,
        if(has(groupUniqArray(subtask_deleted), 0), 'create', 'delete') AS tp
    FROM Tasks
    WHERE task_id IN (SELECT task_id FROM pkg_hashes)
    GROUP BY task_id, subtask_id
)
SELECT
    task_id,
    subtask_id,
    sub_type,
    changed,
    tp,
    toString(TT.titer_srcrpm_hash),
    TT.pkg_name,
    TT.pkg_version,
    TT.pkg_release
FROM tasks_info
LEFT JOIN (
    SELECT
        task_id,
        subtask_id,
        titer_srcrpm_hash,
        PKG.pkg_name AS pkg_name,
        PKG.pkg_version AS pkg_version,
        PKG.pkg_release AS pkg_release
    FROM pkg_hashes
    LEFT JOIN (
        SELECT pkg_name, pkg_hash, pkg_version, pkg_release
        FROM Packages
        WHERE pkg_hash IN (
            SELECT titer_srcrpm_hash FROM pkg_hashes
        )
    ) AS PKG ON PKG.pkg_hash = titer_srcrpm_hash
    GROUP BY
        task_id,
        subtask_id,
        titer_srcrpm_hash,
        PKG.pkg_name,
        PKG.pkg_version,
        PKG.pkg_release
) AS TT ON TT.task_id = tasks_info.task_id AND TT.subtask_id = tasks_info.subtask_id
WHERE sub_type != 'delete' AND tp != 'delete' AND titer_srcrpm_hash != '0'
ORDER BY subtask_id
"""

    get_task_info = """
WITH
t_state AS (
    SELECT
        any(task_id) AS t_id,
        max(task_changed) AS changed,
        argMax(task_state, task_changed) AS state,
        argMax(task_message, task_changed) AS message
    FROM TaskStates
    WHERE task_id = {id}
    AND task_state IN ['DONE', 'TESTED', 'EPERM']
)
SELECT
    t_id AS task_id,
    TI.repo,
    state,
    changed,
    message,
    TI.owner
FROM t_state
LEFT JOIN (
    SELECT
        task_id,
        any(task_repo) AS repo,
        any(task_owner) AS owner
    FROM Tasks
    WHERE subtask_deleted = 0
        AND (task_id, task_changed) = (SELECT t_id, changed FROM t_state)
    GROUP BY task_id
) AS TI ON TI.task_id = t_state.t_id
WHERE task_id IN (
    SELECT task_id FROM (
         SELECT
            task_id,
            subtask_id,
            argMax(subtask_type, ts) AS sub_type,
            argMax(subtask_srpm, ts) AS srpm,
            argMax(subtask_dir, ts) AS dir,
            argMax(subtask_package, ts) AS package,
            if(has(groupUniqArray(subtask_deleted), 0), 'create', 'delete') AS tp
        FROM Tasks
        WHERE task_id = {id}
        GROUP BY task_id, subtask_id
    ) WHERE (sub_type != 'unknown' OR arrayFilter(x -> notEmpty(x), [srpm, package, dir]) != []) AND (tp != 'delete') AND (sub_type != 'delete')
)
"""

    get_subtasks_by_task_id = """
WITH pkg_hashes AS (
    SELECT
        task_id,
        subtask_id,
        argMax(titer_srcrpm_hash, task_changed) as pkg_hash
    FROM TaskIterations
    WHERE task_id = {task_id}
      AND titer_srcrpm_hash != 0
    GROUP BY task_id, subtask_id
)
SELECT
    task_id,
    subtask_id,
    changed,
    pkg_hash,
    pkg_name,
    pkg_version,
    pkg_release,
    chlog_text,
    chlog_date,
    chlog_name,
    chlog_evr,
    EH.errata_id,
    if(EH.discarded_id != '', 1, 0) AS discard,
    EH.eh_created,
    EH.eh_update,
    EH.ref_links,
    EH.ref_types
FROM (
    SELECT *, TT.*
    FROM (
        SELECT
            task_id,
            subtask_id,
            argMax(subtask_type, ts) AS sub_type,
            argMax(subtask_srpm, ts) AS srpm,
            argMax(subtask_dir, ts) AS dir,
            argMax(subtask_package, ts) AS package,
            argMax(subtask_changed, ts) AS changed,
            if(has(groupUniqArray(subtask_deleted), 0), 'create', 'delete') AS tp
        FROM Tasks
        WHERE (task_id = {task_id})
        GROUP BY task_id, subtask_id
    ) AS ST
    LEFT JOIN (
        SELECT
            task_id,
            subtask_id,
            pkg_hash,
            PKG.pkg_name AS pkg_name,
            PKG.pkg_version AS pkg_version,
            PKG.pkg_release AS pkg_release,
            PKG.chlog_text AS chlog_text,
            PKG.chlog_date AS chlog_date,
            PKG.chlog_name AS chlog_name,
            PKG.chlog_evr AS chlog_evr
        FROM pkg_hashes
        LEFT JOIN (
            SELECT
                pkg_name,
                pkg_hash,
                pkg_version,
                pkg_release,
                CHLG.chlog_name,
                CHLG.chlog_nick,
                CHLG.chlog_date,
                CHLG.chlog_text,
                CHLG.chlog_evr
            FROM Packages
            LEFT JOIN
            (
                SELECT
                    pkg_hash,
                    chlog_name,
                    chlog_nick,
                    chlog_date,
                    chlog_text,
                    chlog_evr
                FROM SrcPackagesLastChangelog
                WHERE pkg_hash IN (
                    SELECT pkg_hash FROM pkg_hashes
                )
            ) AS CHLG ON CHLG.pkg_hash = Packages.pkg_hash
            WHERE pkg_hash IN (
                SELECT pkg_hash FROM pkg_hashes
            )
        ) AS PKG ON PKG.pkg_hash = pkg_hashes.pkg_hash
        GROUP BY
            task_id,
            subtask_id,
            pkg_hash,
            pkg_name,
            pkg_version,
            pkg_release,
            chlog_text,
            chlog_date,
            chlog_name,
            chlog_evr
    ) AS TT ON TT.task_id = ST.task_id AND TT.subtask_id = ST.subtask_id
    WHERE (tp != 'delete') AND (sub_type != 'delete') AND (sub_type != 'unknown'
        OR arrayFilter(x -> notEmpty(x), [srpm, package, dir]) != [])
    ORDER BY subtask_id
) AS SI
LEFT JOIN (
    SELECT TT.*, DE.discarded_id as discarded_id
    FROM (
        SELECT
            task_id,
            subtask_id,
            argMax(errata_id, errata_id_version) AS errata_id,
            argMax(eh_references.link, ts) AS ref_links,
            argMax(eh_references.type, ts) AS ref_types,
            max(eh_updated) AS eh_update,
            max(eh_created) AS eh_created
        FROM ErrataHistory
        WHERE eh_type = 'task'
            AND task_id = {task_id}
        GROUP BY subtask_id, task_id
        ORDER BY subtask_id
    ) AS TT
    LEFT JOIN (
        SELECT errata_id AS discarded_id
        FROM last_discarded_erratas
    ) AS DE ON errata_id = DE.discarded_id
) AS EH ON EH.task_id = SI.task_id AND EH.subtask_id = SI.subtask_id
"""

    get_vuln_info_by_ids = """
SELECT
    vuln_id,
    vuln_type,
    vuln_summary,
    vuln_score,
    vuln_severity,
    vuln_url,
    vuln_modified_date,
    vuln_published_date,
    vuln_references.link,
    vuln_references.type
FROM Vulnerabilities
WHERE (vuln_id, vuln_hash) IN (
    SELECT
        vuln_id,
        argMax(vuln_hash, ts)
    FROM Vulnerabilities
    WHERE vuln_id IN (SELECT vuln_id FROM {tmp_table})
    GROUP BY vuln_id
)
ORDER BY vuln_modified_date DESC
"""

    get_related_vulns_by_cves = """
SELECT
    vuln_id,
    vuln_type,
    vuln_summary,
    vuln_score,
    vuln_severity,
    vuln_url,
    vuln_modified_date,
    vuln_published_date,
    vuln_references.link,
    vuln_references.type
FROM Vulnerabilities
WHERE (vuln_id, vuln_hash) IN (
    SELECT
        vuln_id,
        argMax(vuln_hash, ts)
    FROM Vulnerabilities
    WHERE vuln_id IN (
        SELECT vuln_id
        FROM Vulnerabilities
        WHERE arrayExists(x -> x IN {tmp_table}, `vuln_references.link`)
        )
    GROUP BY vuln_id
)
"""

    get_errata_info_template = """
SELECT DISTINCT
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
    arrayZip(eh_references.type, eh_references.link),
    eh_hash,
    if(discarded_id != '', 1, 0)
FROM ErrataHistory
LEFT JOIN (
    SELECT errata_id AS discarded_id
    FROM last_discarded_erratas
) AS DE ON errata_id = DE.discarded_id
{where_clause}
"""

    get_errata_by_id_where_clause = """
WHERE errata_id = '{errata_id}'
"""

    get_bulletin_by_pkg_update_where_clause = """
WHERE errata_id IN (
    WITH bulletins AS (
        SELECT
            errata_id_noversion AS eid_no_ver,
            argMax(errata_id, eh_updated) AS eid
        FROM ErrataHistory
        WHERE eh_type = 'bulletin'
            AND has(eh_references.link, '{errata_id}')
        GROUP BY errata_id_noversion
    )
    SELECT eid
    FROM (
        SELECT argMax(errata_id, eh_updated) AS eid
        FROM ErrataHistory
        WHERE errata_id_noversion IN (SELECT eid_no_ver FROM bulletins)
        GROUP BY errata_id_noversion
    )
    WHERE eid IN (SELECT eid FROM bulletins)
)
"""

    get_bulletin_by_branch_date_where_clause = """
WHERE errata_id IN (
    SELECT DISTINCT eid
    FROM (
        SELECT
            errata_id_noversion,
            argMax(errata_id, eh_updated) AS eid
        FROM ErrataHistory
        WHERE eh_type = 'bulletin'
            AND pkgset_name = '{branch}'
            AND eh_created = '{date}'
        GROUP BY errata_id_noversion
    )
)
"""

    get_errata_by_task_where_clause = """
WHERE errata_id IN (
    SELECT DISTINCT eid
    FROM (
        SELECT
            errata_id_noversion,
            argMax(errata_id, eh_updated) AS eid
        FROM ErrataHistory
        WHERE task_state = 'DONE'
            AND task_id = {task_id}
            AND subtask_id = {subtask_id}
        GROUP BY errata_id_noversion
    )
)
"""

    check_errata_id_is_discarded = """
SELECT countDistinct(errata_id)
FROM last_discarded_erratas
WHERE errata_id = '{errata_id}'
"""

    get_ecc_by_errata_id = """
SELECT
    ec_id_noversion,
    argMax(ec_id, ec_updated)
FROM ErrataChangeHistory
WHERE errata_id LIKE '{errata_id_noversion}-%%'
GROUP BY ec_id_noversion
"""

    store_errata_history = """
INSERT INTO ErrataHistory (* EXCEPT (ts, eh_json)) VALUES
"""

    store_errata_change_history = """
INSERT INTO ErrataChangeHistory (* EXCEPT ts) VALUES
"""

    get_package_info_by_task_and_subtask = """
WITH
(
    SELECT max(task_changed)
    FROM TaskStates
    WHERE task_id = {task_id} AND task_state = 'DONE'
) AS t_changed,
(
    SELECT DISTINCT titer_srcrpm_hash
    FROM TaskIterations
    WHERE task_id = {task_id}
        AND subtask_id = {subtask_id}
        AND task_changed = t_changed
) AS srcrpm_hash
SELECT DISTINCT
    pkg_hash,
    pkg_name,
    pkg_version,
    pkg_release,
    (SELECT DISTINCT task_repo FROM Tasks WHERE task_id  = {task_id}) AS pkgset_name,
    {task_id} AS task_id,
    {subtask_id} AS subtask_id,
    'DONE' AS task_state,
    t_changed AS task_changed
FROM Packages
WHERE pkg_hash = srcrpm_hash
"""

    get_done_tasks = """
SELECT
    task_id,
    task_prev,
    task_changed
FROM TaskStates
WHERE task_state = 'DONE'
    AND task_id IN (
        SELECT DISTINCT
            task_id
        FROM Tasks
        WHERE task_repo = '{branch}'
        AND task_changed >= parseDateTime32BestEffort('{changed}')
    )
    AND task_changed >= parseDateTime32BestEffort('{changed}')
ORDER BY task_changed DESC
"""

    get_nearest_branch_point = """
SELECT
    pkgset_nodename,
    pkgset_date,
    toUInt32(pkgset_kv.v[indexOf(pkgset_kv.k, 'task')])
FROM PackageSetName
WHERE pkgset_depth = 0
    AND pkgset_nodename = '{branch}'
    AND pkgset_date >= parseDateTime32BestEffort('{changed}')
ORDER BY pkgset_date ASC
LIMIT 1
"""

    get_last_branch_state = """
SELECT
    pkgset_nodename,
    pkgset_date,
    toUInt32(pkgset_kv.v[indexOf(pkgset_kv.k, 'task')])
FROM PackageSetName
WHERE pkgset_depth = 0
    AND pkgset_nodename = '{branch}'
ORDER BY pkgset_date {order}
LIMIT 1
"""

    get_bugs_by_ids = """
SELECT
    bz_id,
    argMax(bz_summary, ts),
    argMax(bz_last_changed, ts)
FROM Bugzilla
WHERE bz_id IN (
    SELECT bz_id FROM {tmp_table}
)
GROUP BY bz_id
"""

    get_errata_history = """
WITH
(
    SELECT DISTINCT errata_id_noversion
    FROM ErrataHistory
    WHERE errata_id = '{errata_id}'
) AS eid_noversion,
ec_ids AS (
    SELECT DISTINCT ec_id_noversion
    FROM ErrataChangeHistory
    WHERE ec_id_noversion IN (
        SELECT ec_id_noversion FROM ErrataChangeHistory
        WHERE errata_id  LIKE concat(eid_noversion, '-%')
    )
),
parent_ids as (
    SELECT ec_id,
           errata_id,
           ec_created,
           ec_updated,
           ec_user,
           ec_reason,
           toString(ec_type),
           toString(ec_source),
           EH.links,
           EH.task_id,
           EH.task_state
    FROM (
        SELECT *
        FROM ErrataChangeHistory
        WHERE ec_id_noversion IN (SELECT ec_id_noversion FROM ec_ids)
        {origin}
    ) AS EP
    INNER JOIN (
        SELECT
               errata_id,
               eh_references.link AS links,
               task_id,
               task_state
        FROM ErrataHistory
        WHERE errata_id_noversion = eid_noversion
    ) AS EH ON EH.errata_id = EP.errata_id
)
SELECT * FROM (
    SELECT '' AS ec_id,
           errata_id,
           eh_created,
           eh_updated,
           '' AS ec_user,
           '' AS ec_reason,
           'create' AS ec_type,
           'auto' AS ec_source,
           eh_references.link AS links,
           task_id,
           task_state
    FROM ErrataHistory
    WHERE errata_id IN (
        SELECT errata_id
        FROM ErrataHistory
        where errata_id_noversion = eid_noversion
    )
    AND errata_id NOT IN (SELECT errata_id FROM parent_ids)
    UNION ALL
    SELECT DISTINCT parent_ids.*
    FROM parent_ids
) ORDER BY eh_updated desc
"""

    get_cpes = """
WITH
repology_names AS (
    SELECT
        alt_name,
        repology_name,
        repology_branch
    FROM (
        SELECT
            pkg_name AS alt_name,
            pnc_result AS repology_name,
            pnc_type AS repology_branch,
            argMax(pnc_state, ts) AS state
        FROM PackagesNameConversion
        WHERE pnc_type IN {cpe_branches}
        GROUP BY pkg_name, pnc_result, pnc_type
    ) WHERE state = 'active' {pkg_name_conversion_clause}
)
SELECT
    state,
    alt_name AS pkg_name,
    cpe_pkg_name,
    repology_branch,
    cpe
FROM (
    SELECT
        cpe_pkg_name,
        cpe,
        state
    FROM (
        SELECT
            pkg_name AS cpe_pkg_name,
            argMax(pnc_result, ts) AS cpe,
            argMax(pnc_state, ts) AS state
        FROM PackagesNameConversion
        WHERE pnc_type = 'cpe'
        GROUP BY pkg_name, pnc_result
    ) WHERE state IN {cpe_states}
) AS CPE
{join_type} JOIN repology_names AS EN ON EN.repology_name = cpe_pkg_name
ORDER BY state, repology_name, pkg_name, repology_branch, cpe
"""

    get_cpes_by_project_names = """
SELECT
    pkg_name,
    state,
    cpe,
    'cpe' AS type,
    source
FROM (
    SELECT
        pkg_name,
        argMax(pnc_result, ts) AS cpe,
        argMax(pnc_state, ts) AS state,
        any(pnc_source) AS source
    FROM PackagesNameConversion
    WHERE pnc_type = 'cpe'
    GROUP BY pkg_name, pnc_result
) WHERE state IN {cpe_states}
    AND pkg_name IN {tmp_table}
"""

    get_packages_by_project_names = """
SELECT DISTINCT alt_name
FROM (
    SELECT
        pkg_name AS alt_name,
        pnc_result AS repology_name,
        argMax(pnc_state, ts) AS state
    FROM PackagesNameConversion
    WHERE pnc_type IN {cpe_branches}
    GROUP BY pkg_name, pnc_result, pnc_type
) WHERE state = 'active' AND repology_name in {tmp_table}
"""

    store_pnc_records = """
INSERT INTO PackagesNameConversion VALUES
"""

    store_pnc_change_records = """
INSERT INTO PncChangeHistory (* EXCEPT ts) VALUES
"""

    tmp_maintainer_pkg_by_nick_acl = """
CREATE TEMPORARY TABLE {tmp_table} AS
SELECT pkg_hash, pkgset_name, pkg_version, pkg_release FROM (
    SELECT DISTINCT pkg_hash, pkgset_name, pkg_version, pkg_release
    FROM static_last_packages
    WHERE pkg_sourcepackage = 1
          AND pkgset_name IN ({branches})
          AND pkg_name IN (
            SELECT acl_for
            FROM last_acl_stage1
            WHERE acl_branch = 'sisyphus'
              AND has(acl_list, '{maintainer_nickname}')
    )
)
"""

    tmp_maintainer_pkg_by_nick_leader_acl = """
CREATE TEMPORARY TABLE {tmp_table} AS
SELECT pkg_hash, pkgset_name, pkg_version, pkg_release FROM (
    SELECT DISTINCT pkg_hash, pkgset_name, pkg_version, pkg_release
    FROM static_last_packages
    WHERE pkg_sourcepackage = 1
          AND pkgset_name IN ({branches})
          AND pkg_name IN (
            SELECT pkgname
            FROM last_acl_with_groups
            WHERE acl_branch = 'sisyphus'
              AND acl_user = '{maintainer_nickname}'
              AND order_u = 1
              AND order_g = 0
        )
)
"""

    tmp_maintainer_pkg_by_nick_or_group_acl = """
CREATE TEMPORARY TABLE {tmp_table} AS
SELECT pkg_hash, pkgset_name, pkg_version, pkg_release FROM (
    WITH
    (
        SELECT groupUniqArray(acl_for)
        FROM last_acl_stage1
        WHERE has(acl_list, '{maintainer_nickname}')
            AND acl_for LIKE ('@%')
            AND acl_branch = 'sisyphus'
    ) AS acl_group
    SELECT DISTINCT pkg_hash, pkgset_name, pkg_version, pkg_release
    FROM static_last_packages
    WHERE pkg_sourcepackage = 1
          AND pkgset_name IN ({branches})
          AND pkg_name IN (
            SELECT acl_for
            FROM last_acl_stage1
            WHERE acl_branch = 'sisyphus'
              AND (has(acl_list, '{maintainer_nickname}')
              OR hasAny(acl_list, acl_group))
        )
)
"""

    tmp_maintainer_pkg_by_nick_leader_and_group_acl = """
CREATE TEMPORARY TABLE {tmp_table} AS
SELECT pkg_hash, pkgset_name, pkg_version, pkg_release FROM (
    SELECT DISTINCT pkg_hash, pkgset_name, pkg_version, pkg_release
    FROM static_last_packages
    WHERE pkg_sourcepackage = 1
          AND pkgset_name IN ({branches})
          AND pkg_name IN (
            SELECT pkgname
            FROM last_acl_with_groups
            WHERE acl_user = '{maintainer_nickname}'
                AND acl_branch = 'sisyphus'
                AND order_u = 1
    )
)
"""

    tmp_maintainer_pkg = """
CREATE TEMPORARY TABLE {tmp_table} AS
SELECT pkg_hash, pkgset_name, pkg_version, pkg_release FROM (
    SELECT DISTINCT pkg_hash, pkgset_name, pkg_version, pkg_release
    FROM last_packages
    WHERE pkg_sourcepackage = 1
        AND pkgset_name IN ({branches})
        AND pkg_packager_email LIKE '{maintainer_nickname}@%'
)
"""

    get_maintainer_open_vulns = """
WITH vulns AS (
    SELECT pkg_hash,
           pkg_name,
           TT.pkgset_name AS branch,
           TT.pkg_version AS version,
           TT.pkg_release AS release,
           vuln_id,
           vuln_hash
    FROM (
        SELECT pkg_name,
               vuln_id,
               pkg_hash,
               argMax(is_vulnerable, ts) AS is_vulnerable,
               argMax(vuln_hash, ts) AS vuln_hash
        FROM PackagesCveMatch
        GROUP BY pkg_name, vuln_id, pkg_hash
    ) AS ES
     LEFT JOIN (
        SELECT pkg_hash, pkgset_name, pkg_version, pkg_release
        FROM {tmp_table}
    ) AS TT ON TT.pkg_hash == ES.pkg_hash
    WHERE pkg_hash IN (
        SELECT pkg_hash FROM {tmp_table}
    ) AND is_vulnerable = 1
    GROUP BY pkg_name, pkg_hash, vuln_id, vuln_hash, branch, version, release
)
SELECT * FROM (
    SELECT pkg_hash,
           pkg_name,
           version,
           release,
           max(VUL.vuln_modified_date) AS modified,
           branch,
           arrayReverseSort((x) -> x.1, groupUniqArray((vuln_id, VUL.vuln_type, VUL.vuln_severity))) AS vulns
    FROM vulns
    LEFT JOIN (
        SELECT
            vuln_id,
            vuln_hash,
            vuln_type,
            vuln_severity,
            vuln_modified_date
        FROM Vulnerabilities
    ) AS VUL ON VUL.vuln_id = vulns.vuln_id AND VUL.vuln_hash = vulns.vuln_hash
    GROUP BY pkg_name, pkg_hash, branch, version, release
)
{where_clause}
"""

    get_all_open_vulns = """
SELECT DISTINCT
    RES.pkg_hash,
    RES.pkg_name,
    PKG.pkg_version,
    PKG.pkg_release,
    RES.modified_date,
    RES.pkgset_name,
    RES.vulns
FROM (
SELECT pkg_hash,
       pkg_name,
       pkgset_name,
       arrayReverseSort((x) -> x.1, groupArray((vuln_id, 'CVE', vuln_severity))) as vulns,
       max(TT.vuln_modified_date) as modified_date
FROM (
    SELECT pkg_hash,
           pkg_name,
           pkgset_name,
           vuln_id,
           any(vuln_hash) as vuln_hash,
           has(groupArray(is_vulnerable), 1) as is_vuln,
           has(groupArray(is_fixed), 1) as is_fix
    FROM PackagesVulnerabilityStatus
    WHERE pkgset_name IN ({branches})
    {where_clause}
    GROUP BY pkg_name, pkgset_name, vuln_id, pkg_hash
) AS vuln_status
LEFT JOIN (
    SELECT vuln_hash, vuln_severity, vuln_modified_date
    FROM Vulnerabilities
) AS TT ON TT.vuln_hash = vuln_status.vuln_hash
WHERE is_fix = 0 and is_vuln = 1
{severity}
GROUP BY pkg_hash, pkg_name, pkgset_name
) AS RES
LEFT JOIN (
    SELECT pkg_hash, pkg_version, pkg_release
    FROM static_last_packages
    WHERE pkgset_name IN ({branches})
) AS PKG ON PKG.pkg_hash = RES.pkg_hash
{maintainer_clause}
"""

    get_pkg_images = """
WITH pkgs AS (
    SELECT pkg_name, pkg_hash, pkg_sourcepackage, pkg_srcrpm_hash
    FROM Packages
    WHERE pkg_hash IN (
        SELECT DISTINCT pkg_hash
        FROM Packages
        WHERE pkg_srcrpm_hash IN {tmp_table}
    )
)
SELECT src_hash,
        pkgname,
        img_branch,
        groupUniqArray((img_tag, img_file, IT.img_show)) AS tags
FROM (
    SELECT DISTINCT
        TT.pkg_srcrpm_hash AS src_hash,
        TT.pkg_name AS pkgname,
        img_branch,
        img_tag,
        img_file
    FROM lv_all_image_packages
    LEFT JOIN (
        SELECT DISTINCT PN.pkg_name AS pkg_name, pkg_hash, pkg_srcrpm_hash FROM pkgs
        LEFT JOIN (
            SELECT pkg_name, pkg_hash FROM pkgs
        ) AS PN ON PN.pkg_hash = pkg_srcrpm_hash
        WHERE pkg_sourcepackage = 0
    ) AS TT ON TT.pkg_hash = lv_all_image_packages.pkg_hash
    WHERE pkg_hash IN (
        SELECT DISTINCT pkg_hash
        FROM pkgs
        WHERE pkg_sourcepackage = 0
    ) GROUP BY pkgname, src_hash, img_branch, img_tag, img_file
    ORDER BY img_file
) AS imgs
LEFT JOIN (
        SELECT img_tag,
               argMax(img_show, ts) AS img_show
        FROM ImageTagStatus
        GROUP BY img_tag
) AS IT ON IT.img_tag = imgs.img_tag
GROUP BY pkgname, src_hash, img_branch
"""

    get_packages_info_by_hashes = """
SELECT DISTINCT
    toString(pkg_hash),
    pkg_name,
    pkg_version,
    pkg_release,
    pkgset_name
FROM static_last_packages
WHERE pkg_hash IN {tmp_table}
"""

    get_pkg_cve_matches_by_hashes = """
SELECT DISTINCT
    pkg_hash,
    pkg_name,
    pkg_cpe,
    pkg_cpe_hash,
    vuln_id,
    vuln_hash,
    cpm_cpe,
    cpm_cpe_hash,
    cpm_version_hash,
    is_vulnerable
FROM PackagesCveMatch
WHERE (key_hash, ts) IN (
    SELECT key_hash, max(ts)
    FROM PackagesCveMatch
    WHERE key_hash IN {tmp_table}
    GROUP BY key_hash
)
"""

    get_cpes_by_vulns = """
SELECT cpe
FROM (
    SELECT cpe_hash,
           argMax(cpm_cpe, ts) as cpe
    FROM CpeMatch
    WHERE vuln_id IN {cves}
    GROUP BY cpe_hash
)
"""

    find_cpe = """
WITH
repology_names AS (
    SELECT
        alt_name,
        repology_name,
        repology_branch
    FROM (
        SELECT
            pkg_name AS alt_name,
            pnc_result AS repology_name,
            pnc_type AS repology_branch,
            argMax(pnc_state, ts) AS state
        FROM PackagesNameConversion
        WHERE pnc_type IN {pnc_branches}
        GROUP BY pkg_name, pnc_result, pnc_type
    ) WHERE state = 'active'
)
SELECT
    state,
    alt_name AS pkg_name,
    repology_name,
    repology_branch,
    cpe
FROM (
    SELECT
        cpe_pkg_name,
        cpe,
        state
    FROM (
        SELECT
            pkg_name AS cpe_pkg_name,
            argMax(pnc_result, ts) AS cpe,
            argMax(pnc_state, ts) AS state
        FROM PackagesNameConversion
        WHERE pnc_type = 'cpe'
        GROUP BY pkg_name, pnc_result
    ) {state}
) AS CPE
INNER JOIN repology_names AS EN ON EN.repology_name = cpe_pkg_name
{where}
ORDER BY state, repology_name, pkg_name, repology_branch, cpe;
"""

    get_pnc_records = """
SELECT
    name,
    state,
    result,
    type,
    source
FROM (
    SELECT
        pkg_name AS name,
        argMax(pnc_state, ts) AS state,
        pnc_result AS result,
        pnc_type AS type,
        argMax(pnc_source, ts) AS source
    FROM PackagesNameConversion
    WHERE pnc_type IN {pnc_branches}
    GROUP BY
        pkg_name,
        pnc_type,
        pnc_result
)
{where_clause}
ORDER BY name, type, result
"""

    get_pnc_list = """
SELECT * FROM (
    SELECT
        state,
        result,
        groupArray((name, type, source)) as pkgs
    FROM (
        SELECT
            pkg_name AS name,
            argMax(pnc_state, ts) AS state,
            pnc_result AS result,
            pnc_type AS type,
            argMax(pnc_source, ts) AS source
        FROM PackagesNameConversion
        WHERE pnc_type IN {pnc_branches}
        GROUP BY
            pkg_name,
            pnc_type,
            pnc_result
        ORDER BY pkg_name, type
    )
    WHERE type IN {branch}
GROUP BY result, state
) {where_clause}
ORDER BY result, state
"""

    get_unmapped_packages = """
SELECT DISTINCT
    pkg_name
FROM static_last_packages
WHERE {name_like}
    AND pkg_sourcepackage = 1
    AND pkg_name not in (
        SELECT pkg_name FROM (
            SELECT
                pkg_name,
                argMax(pnc_state, ts) AS state
            FROM PackagesNameConversion
            WHERE pnc_type IN {pnc_branches}
            GROUP BY
                pkg_name,
                pnc_type,
                pnc_result
            ORDER BY pkg_name
        ) WHERE state != 'inactive' AND {name_like}
    )
ORDER BY pkg_name
"""

    get_vuln_list = """
SELECT VULNS.*
FROM (
    SELECT vuln_id,
           argMax(vuln_severity, ts) AS severity,
           argMax(vuln_summary, ts) AS summary,
           argMax(vuln_modified_date, ts) AS modified,
           argMax(vuln_published_date, ts) AS published
    FROM Vulnerabilities
    GROUP BY vuln_id
) AS VULNS
{where_clause} {where_clause2}
GROUP BY vuln_id, severity, summary, modified, published
ORDER BY  modified DESC
"""

    get_erratas_vuln = """
WITH cve_match AS (
    SELECT cpm_cpe FROM (
        SELECT cpm_cpe,
               argMax(is_vulnerable, ts) AS is_vulnerable,
               argMax(vuln_hash, ts) AS vuln_hash
        FROM PackagesCveMatch
        GROUP BY cpm_cpe
    )
)
SELECT vuln_id, errata_ids, cpes, arrayAll(x -> (x in cve_match), cpes) as our
FROM (
    SELECT vuln_id,
           ERR.errata_ids as errata_ids,
           groupUniqArray(cpm_cpe) as cpes
    FROM CpeMatch
    LEFT JOIN (
        SELECT vuln_id,
               groupUniqArray((errata_id, task_state)) AS errata_ids
        FROM (
            SELECT
                errata_id,
                task_state,
                arrayJoin(links) AS vuln_id
            FROM
            (
                SELECT errata_id,
                       task_state,
                       `eh_references.link` as links
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
                    GROUP BY errata_id_noversion
                )
                WHERE eid NOT IN (
                    SELECT errata_id FROM last_discarded_erratas
                )
            )
            )
        ) {where_clause1}
        GROUP BY vuln_id
    ) AS ERR ON ERR.vuln_id = CpeMatch.vuln_id
    {where_clause1}
    GROUP BY vuln_id, errata_ids
) {where_clause2}
"""


sql = SQL()
