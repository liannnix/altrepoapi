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
    count() OVER() AS total_count
FROM
(
    SELECT DISTINCT
        pkg_packager,
        substring(pkg_packager_email, 1, position(pkg_packager_email, '@') - 1) AS packager_nick,
        countDistinct(pkg_hash) AS cnt
    FROM last_packages
    WHERE pkg_sourcepackage = 1
    {branch}
    {nickname}
    GROUP BY
        pkg_packager,
        packager_nick
)
GROUP BY packager_nick
ORDER BY lower(name)
{limit}
{page}
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
SELECT *, count() OVER() as total_count
FROM (
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
{limit} {page}
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
    select_pkg_hash_by_nick_acl = """
SELECT DISTINCT pkg_hash
FROM static_last_packages
WHERE pkg_sourcepackage = 1
    AND pkgset_name IN {branches}
    AND pkg_name IN (
        SELECT acl_for
        FROM last_acl_stage1
        WHERE acl_branch = 'sisyphus'
            AND has(acl_list, '{maintainer_nickname}')
    )
"""

    select_pkg_hash_by_nick_leader_acl = """
SELECT DISTINCT pkg_hash
FROM static_last_packages
WHERE pkg_sourcepackage = 1
    AND pkgset_name IN {branches}
    AND pkg_name IN (
        SELECT pkgname
        FROM last_acl_with_groups
        WHERE acl_branch = 'sisyphus'
            AND acl_user = '{maintainer_nickname}'
            AND order_u = 1
            AND order_g = 0
    )
"""

    select_pkg_hash_by_nick_or_group_acl = """
WITH (
    SELECT groupUniqArray(acl_for)
    FROM last_acl_stage1
    WHERE has(acl_list, '{maintainer_nickname}')
        AND acl_for LIKE '@%'
        AND acl_branch = 'sisyphus'
) AS acl_group
SELECT DISTINCT pkg_hash
FROM static_last_packages
WHERE pkg_sourcepackage = 1
    AND pkgset_name IN {branches}
    AND pkg_name IN (
        SELECT acl_for
        FROM last_acl_stage1
        WHERE acl_branch = 'sisyphus'
            AND (has(acl_list, '{maintainer_nickname}') OR hasAny(acl_list, acl_group))
    )
"""

    select_pkg_hash_by_nick_leader_and_group_acl = """
SELECT DISTINCT pkg_hash
FROM static_last_packages
WHERE pkg_sourcepackage = 1
    AND pkgset_name IN {branches}
    AND pkg_name IN (
        SELECT pkgname
        FROM last_acl_with_groups
        WHERE acl_user = '{maintainer_nickname}'
            AND acl_branch = 'sisyphus'
            AND order_u = 1
    )
"""

    select_pkg_hash_by_packager = """
SELECT DISTINCT pkg_hash
FROM last_packages
WHERE pkg_sourcepackage = 1
    AND pkgset_name IN {branches}
    AND pkg_packager_email LIKE '{maintainer_nickname}@%'
"""

    get_all_open_vulns = """
WITH VulnerablePackages AS (
    SELECT
        pkg_hash,
        pkg_name,
        pkgset_name,
        vuln_id,
        vuln_hash
    FROM PackagesVulnerabilityStatus
    {where_clause}
    GROUP BY
        pkg_hash,
        pkg_name,
        pkgset_name,
        vuln_id,
        vuln_hash
    HAVING has(groupArray(is_vulnerable), 1)
        AND (NOT has(groupArray(is_fixed), 1))
),
RelatedVulnerabilities AS (
    SELECT
        arrayJoin(vuln_cves).2 AS cve_id,
        groupUniqArray((vuln_id, vuln_type, vuln_hash)) AS related_vulns
    FROM (
        SELECT
            vuln_id,
            vuln_type,
            argMax(vuln_hash, ts) AS vuln_hash,
            arrayFilter(
                (t, l) -> (t = 'CVE'),
                arrayZip(
                    argMax(vuln_references.type, ts),
                    argMax(vuln_references.link, ts)
                )
            ) AS vuln_cves
        FROM Vulnerabilities
        WHERE vuln_type IN {vuln_types}
        GROUP BY
            vuln_id,
            vuln_type
    ) AS L
    WHERE cve_id IN (SELECT DISTINCT vuln_id FROM VulnerablePackages)
    GROUP BY cve_id
),
PackagesOpenVulnerabilities AS (
    SELECT
        pkg_hash,
        pkg_name,
        pkgset_name,
        vuln.1 AS vuln_id,
        vuln.2 AS vuln_type,
        vuln.3 AS vuln_hash,
        vuln_severity,
        vuln_modified_date
    FROM (
        SELECT
            pkg_hash,
            pkg_name,
            pkgset_name,
            arrayJoin(
                arrayUnion(
                    related_vulns,
                    [(vuln_id, 'CVE', vuln_hash)]
                )
            ) AS vuln
        FROM VulnerablePackages AS VP
        INNER JOIN RelatedVulnerabilities AS RV
        ON VP.vuln_id = RV.cve_id
    ) AS L
    LEFT JOIN (
        SELECT DISTINCT
            vuln_hash,
            vuln_severity,
            vuln_modified_date
        FROM Vulnerabilities
    ) AS V ON vuln_hash = V.vuln_hash
    {severity_where_clause}
)
SELECT DISTINCT
    RES.pkg_hash,
    RES.pkg_name,
    PKG.pkg_version,
    PKG.pkg_release,
    RES.modified_date,
    RES.pkgset_name,
    RES.vulns,
    (countDistinct(*) OVER())
FROM (
    SELECT
        pkg_hash,
        pkg_name,
        pkgset_name,
        arrayReverseSort(
            (x) -> x.1,
            groupArray((vuln_id, vuln_type, vuln_severity))
        ) as vulns,
        max(vuln_modified_date) AS modified_date
    FROM PackagesOpenVulnerabilities AS POV
    GROUP BY
        pkg_hash,
        pkg_name,
        pkgset_name
) AS RES
LEFT JOIN (
    SELECT
        pkg_hash,
        pkg_version,
        pkg_release
    FROM static_last_packages
    WHERE pkgset_name IN {branches}
) AS PKG ON PKG.pkg_hash = RES.pkg_hash
{final_where_clause}
{order_by_clause}
{limit_clause}
{offset_clause}
"""

    get_pkg_images = """
WITH pkgs AS (
    SELECT
        pkg_name,
        pkg_hash,
        pkg_srcrpm_hash
    FROM Packages
    WHERE pkg_srcrpm_hash IN {tmp_table}
        AND pkg_sourcepackage=0
)
SELECT
    src_hash,
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
    LEFT JOIN pkgs AS TT ON TT.pkg_hash = lv_all_image_packages.pkg_hash
    WHERE pkg_hash IN (SELECT DISTINCT pkg_hash FROM pkgs)
) AS imgs
LEFT JOIN (
    SELECT
        img_tag,
        argMax(img_show, ts) AS img_show
    FROM ImageTagStatus
    GROUP BY img_tag
) AS IT ON IT.img_tag = imgs.img_tag
GROUP BY
    pkgname,
    src_hash,
    img_branch
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

    get_pnc_list = """
SELECT *, count() OVER() as total_count
FROM (
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
{limit} {page}
"""

    get_unmapped_packages = """
SELECT DISTINCT
    pkg_name
FROM static_last_packages
WHERE {name_like}
    AND pkg_sourcepackage = 1
    AND pkgset_name IN {branches}
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

    get_all_packages = """
SELECT DISTINCT
    pkg_name
FROM static_last_packages
WHERE {name_like}
    AND pkg_sourcepackage = 1
    AND pkgset_name IN {branches}
ORDER BY pkg_name
"""

    get_vuln_list = """
SELECT
    vuln_id AS id,
    severity,
    status,
    resolution,
    summary,
    modified,
    published,
    errata_ids,
    cpes,
    our,
    count() OVER () AS total_count
FROM (
    SELECT
        vulns.vuln_id,
        argMax(vulns.vuln_severity, vulns.ts) AS severity,
        argMax(vs.vs_status, vs.ts) AS status,
        argMax(vs.vs_resolution, vs.ts) AS resolution,
        argMax(vulns.vuln_summary, vulns.ts) AS summary,
        argMax(vulns.vuln_modified_date, vulns.ts) AS modified,
        argMax(vulns.vuln_published_date, vulns.ts) AS published
    FROM Vulnerabilities AS vulns
    LEFT JOIN VulnerabilityStatus AS vs ON vulns.vuln_id = vs.vuln_id
    {where_vuln_input}
    GROUP BY vulns.vuln_id
    {having_vulns}
) AS base_vulns
LEFT JOIN (
    SELECT
        cm.vuln_id as vuln_id,
        arrayFilter(
            t -> t.1 != '' AND t.1 IS NOT NULL,
            groupUniqArray((eh.errata_id, eh.task_state))
        ) AS errata_ids,
        groupUniqArray(cm.cpm_cpe) AS cpes,
        max(p.cpm_cpe_hash IS NOT NULL) AS our
    FROM CpeMatch AS cm
    LEFT JOIN (
        SELECT DISTINCT cpm_cpe_hash FROM PackagesCveMatch
    ) AS p ON cm.cpe_hash = p.cpm_cpe_hash
    LEFT JOIN (
        SELECT
            errata_id,
            task_state,
            arrayJoin(`eh_references.link`) AS vuln_id
        FROM ErrataHistory
        WHERE (errata_id, eh_updated) IN (
            SELECT
                argMax(errata_id, eh_updated) AS eid,
                max(eh_updated) AS max_ts
            FROM ErrataHistory
            WHERE eh_type IN ('branch', 'task')
            GROUP BY errata_id_noversion
            HAVING eid NOT IN (SELECT errata_id FROM last_discarded_erratas)
        )
    ) AS eh ON eh.vuln_id = cm.vuln_id
    GROUP BY cm.vuln_id
) AS extras ON base_vulns.vuln_id = extras.vuln_id
{where_clause}
{order_by}
{limit}
{page}
"""

    get_change_history = """
WITH base_data AS (
    SELECT * FROM (
        SELECT DISTINCT
            toStartOfSecond(any(ts)) as event_date,
            any(author) as author,
            groupUniqArray(module) as modules,
            arrayReverseSort(x -> x['module'], groupArray(details)) as changes,
            transaction_id
        FROM (
            SELECT
                ts,
                ec_user as author,
                'errata' as module,
                map(
                    'change_type', toString(ec_type),
                    'module', 'errata',
                    'errata_id', errata_id,
                    'message', JSONExtractString(ec_reason, 'message'),
                    'details', JSONExtractRaw(ec_reason, 'details')
                ) as details,
                transaction_id
            FROM ErrataChangeHistory
            UNION ALL
            SELECT DISTINCT
                ts,
                pncc_user as author,
                'pnc' as module,
                map(
                    'change_type', toString(pncc_type),
                    'module', 'pnc',
                    'package_name', pkg_name,
                    'result', pnc_result,
                    'message', JSONExtractString(pncc_reason, 'message'),
                    'details', JSONExtractRaw(pncc_reason, 'details')
                ) as details,
                transaction_id
            FROM PncChangeHistory
        )
        GROUP BY transaction_id
    ) {where_clause}
),
(
    SELECT count() as total FROM base_data
) AS total_count
SELECT
    *,
    total_count
FROM base_data
{order_by}
{limit} {page}
"""

    get_authors_change_history = """
SELECT * FROM (
    SELECT ec_user AS author FROM ErrataChangeHistory GROUP BY author
    UNION DISTINCT
    SELECT pncc_user AS author FROM PncChangeHistory GROUP BY author
) ORDER BY lower(author)
"""

    check_comment_exists = """
SELECT count(comment_id)
FROM Comments
WHERE comment_id = '{id}'
"""

    get_comment_by_id = """
SELECT * FROM Comments
WHERE comment_id = {id}
"""

    get_comments_list = """
SELECT
    c.comment_id,
    c.comment_pid,
    c.comment_rid,
    c.comment_entity_type,
    c.comment_entity_link,
    c.comment_author,
    c.comment_text,
    c.comment_references,
    c.comment_created,
    last_action = 'discard' AS is_discarded
FROM Comments c
LEFT JOIN (
    SELECT
        comment_id,
        argMax(cc_action, ts) AS last_action
    FROM CommentsChangeHistory
    GROUP BY comment_id
) AS h ON c.comment_id = h.comment_id
WHERE
    c.comment_entity_type = '{entity_type}'
    AND c.comment_entity_link = '{entity_link}'
ORDER BY c.comment_id ASC;
"""

    get_last_comment = """
SELECT * from Comments
WHERE
    comment_entity_type = '{entity_type}'
    AND comment_entity_link = '{entity_link}'
ORDER BY comment_id DESC
LIMIT 1
"""

    store_comment = """
INSERT INTO Comments VALUES
"""

    store_comment_change_history = """
INSERT INTO CommentsChangeHistory (* EXCEPT(ts)) VALUES
"""

    get_default_reasons_list = """
SELECT
    dr_text,
    dr_source,
    dr_action,
    argMax(dr_is_active, ts) as dr_is_active,
    argMax(dr_is_deleted, ts) AS is_deleted,
    max(ts) as updated,
    count(*) OVER() as total_count
FROM DefaultReasons
{where_clause}
GROUP BY dr_text, dr_source, dr_action
HAVING is_deleted = 0
    {having_clause}
{order_by}
{limit} {offset}
"""

    store_default_reason = """
INSERT INTO DefaultReasons (* EXCEPT(ts)) VALUES
"""

    get_count_distinct_by_vuln_id = """
SELECT countDistinct(vuln_id) FROM Vulnerabilities WHERE vuln_id = '{vuln_id}'
"""

    get_vuln_status_by_vuln_id = """
SELECT
    vuln_id,
    argMax(vs_author, ts),
    argMax(vs_status, ts),
    argMax(vs_reason, ts),
    argMax(vs_resolution, ts),
    argMax(vs_subscribers, ts),
    argMax(vs_json, ts),
    argMax(vs_updated, ts)
FROM VulnerabilityStatus
WHERE vuln_id = '{vuln_id}'
GROUP BY vuln_id
"""

    store_vuln_status = """
INSERT INTO VulnerabilityStatus (* EXCEPT(vs_updated)) VALUES
"""

    vuln_status_list = """
SELECT
    vuln_id,
    argMax(vs_author, ts) AS author,
    argMax(vs_status, ts) AS status,
    argMax(vs_resolution, ts) AS resolution,
    argMax(vs_reason, ts) AS reason,
    argMax(vs_subscribers, ts) AS subscribers,
    argMax(vs_json, ts) AS json,
    argMax(vs_updated, ts) AS updated,
    count(*) OVER() AS total_count
FROM VulnerabilityStatus
GROUP BY vuln_id
{having_clause}
{order_by_clause}
{limit_clause}
{page_clause}
"""

    vuln_status_history = """
SELECT
    vuln_id,
    vs_author,
    vs_status,
    vs_resolution,
    vs_reason,
    vs_subscribers,
    vs_json,
    vs_updated
FROM VulnerabilityStatus
WHERE vuln_id = '{vuln_id}'
ORDER BY vs_updated DESC
"""

    vuln_status_select_next = """
SELECT vuln_id
FROM Vulnerabilities
LEFT JOIN (
    SELECT
        vuln_id,
        argMax(vs_status, vs_updated) AS last_vs_status,
        argMax(vs_resolution, vs_updated) AS last_vs_resolution,
        max(vs_updated) AS last_vs_updated
    FROM VulnerabilityStatus
    GROUP BY vuln_id
) AS LVS USING vuln_id
WHERE vuln_hash IN (
    SELECT argMax(vuln_hash, ts)
    FROM Vulnerabilities
    GROUP BY vuln_id
)
AND vuln_modified_date >= last_vs_updated
AND last_vs_status != 'working'
{vuln_our_condition}
{current_vuln_id_condition}
{vuln_severity_condition}
{vuln_type_condition}
{published_date_interval_condition}
{modified_date_interval_condition}
{is_errata_condition}
ORDER BY
    vuln_modified_date DESC,
    vuln_id DESC
LIMIT 1
"""

    vuln_status_select_next_is_errata_sub = """
SELECT DISTINCT
    arrayJoin(
        arrayFilter(
            (t, l) -> (t = 'vuln'),
            arrayZip(eh_references.type, eh_references.link)
        )
    ).2 AS vuln_id
FROM ErrataHistory
WHERE errata_id IN (
    SELECT argMax(errata_id, ts)
    FROM ErrataHistory
    GROUP BY errata_id_noversion
)
"""

    get_errata_user = """
SELECT
    user,
    argMax(group, ts) AS last_group,
    argMax(roles, ts) AS last_roles,
    get_errata_user_aliases('{user}') AS aliases,
    argMax(display_name, ts) AS name
FROM ErrataUsers
WHERE user = get_errata_user_original_name('{user}')
GROUP BY user
"""

    get_users_display_names = """
SELECT
    user,
    argMax(display_name, ts) AS name
FROM ErrataUsers
WHERE user IN {tmp_table}
GROUP BY user
"""

    get_most_relevant_users = """
WITH '{input}' AS query
SELECT
    user,
    argMax(group, ts) AS g
FROM ErrataUsers
WHERE (positionCaseInsensitiveUTF8(user, query) AS pos) != 0
GROUP BY user
ORDER BY
    if((eq = 0) AND (st = 0), pos, 0) ASC,
    toUInt8(lower(user) = query) AS eq DESC,
    startsWithUTF8(lower(user), query) AS st DESC,
    length(user) ASC
LIMIT {limit}
"""

    get_user_last_activities = """
WITH
get_errata_user_aliases('{user}') AS target_user,
{limit} AS target_limit,
_last_vuln_status_changes_by_author AS (
    SELECT
        vuln_id,
        vs_author,
        vs_updated
    FROM VulnerabilityStatus
    WHERE has(target_user, vs_author)
    ORDER BY vs_updated DESC
    LIMIT target_limit
),
last_vuln_statuses AS (
    SELECT
        'vuln_status' AS type,
        vuln_id AS id,
        'update' AS action,
        '' AS attr_type,
        '' AS attr_link,
        map(
            'text', ((arraySlice(vs_history, arrayFirstIndex(vs -> ((vs.1, vs.2, vs.8) = (R.vuln_id, R.vs_author, R.vs_updated)), vs_history), 2) AS vcs)[1]).5,
            'new', (vcs[1]).3,
            'old', (vcs[2]).3
        ) AS info_json,
        vs_updated AS date
    FROM
    (
        SELECT
            vuln_id,
            arrayReverseSort(vs -> (vs.8), groupUniqArray(tuple(*))) AS vs_history
        FROM VulnerabilityStatus
        WHERE vuln_id IN (
            SELECT vuln_id
            FROM _last_vuln_status_changes_by_author
        )
        GROUP BY vuln_id
    ) AS VulnStatusHistory
    RIGHT JOIN _last_vuln_status_changes_by_author AS R USING (vuln_id)
),
last_comments AS (
    SELECT
        'comment' AS type,
        CAST(comment_id, 'String') AS id,
        CAST(cc_action, 'String') AS action,
        comment_entity_type AS attr_type,
        comment_entity_link AS attr_link,
        map('text', comment_text) AS info_json,
        comment_created AS date
    FROM Comments
    RIGHT JOIN
    (
        SELECT
            comment_id,
            cc_action
        FROM CommentsChangeHistory
        WHERE has(target_user, cc_user)
        ORDER BY ts DESC
        LIMIT target_limit
    ) AS R USING (comment_id)
    ORDER BY date DESC
),
last_errata AS (
    SELECT
        'errata' AS type,
        errata_id AS id,
        CAST(ec_type, 'String') AS action,
        'package' AS attr_type,
        ec_id AS attr_link,
        map('text', JSONExtractString(ec_reason, 'message')) AS info_json,
        ec_updated AS date
    FROM ErrataChangeHistory
    WHERE startsWith(errata_id, 'ALT-PU')
        AND (ec_source = 'manual')
        AND (ec_origin = 'parent')
        AND (has(target_user, ec_user))
    ORDER BY date DESC
    LIMIT target_limit
),
last_exclusions AS (
    SELECT
        'exclusion' AS type,
        errata_id AS id,
        CAST(ec_type, 'String') AS action,
        JSONExtractString(eh_json, 'type') AS attr_type,
        ec_id AS attr_link,
        map('text', JSONExtractString(eh_json, 'reason')) AS info_json,
        ec_updated AS date
    FROM ErrataHistory
    RIGHT JOIN (
        SELECT
            ec_id,
            ec_type,
            errata_id,
            ec_updated
        FROM ErrataChangeHistory
        WHERE startsWith(errata_id, 'ALT-SA')
            AND (ec_source = 'manual')
            AND (ec_origin = 'parent')
            AND (has(target_user, ec_user))
        ORDER BY ec_updated DESC
        LIMIT target_limit
    ) AS R USING (errata_id)
    ORDER BY date DESC
),
last_cpes AS (
    SELECT
        'cpe' AS type,
        pkg_name AS id,
        CAST(pncc_type, 'String') AS action,
        pnc_type AS attr_type,
        pnc_result AS attr_link,
        map('text', JSONExtractString(pncc_reason, 'message')) AS info_json,
        ts AS date
    FROM PncChangeHistory
    WHERE (pnc_type = 'cpe')
        AND (pncc_source = 'manual')
        AND (pncc_origin = 'parent')
        AND (has(target_user, pncc_user))
    ORDER BY date DESC
    LIMIT target_limit
),
last_pncs AS (
    SELECT
        'pnc' AS type,
        pnc_result AS id,
        CAST(pncc_type, 'String') AS action,
        'pnc' AS attr_type,
        pkg_name AS attr_link,
        map('text', JSONExtractString(pncc_reason, 'message')) AS info_json,
        ts AS date
    FROM PncChangeHistory
    WHERE (pnc_type != 'cpe')
        AND (pncc_source = 'manual')
        AND (pncc_origin = 'parent')
        AND (has(target_user, pncc_user))
    ORDER BY date DESC
    LIMIT target_limit
)
SELECT * FROM (
    SELECT * FROM last_vuln_statuses
    UNION ALL
    SELECT * FROM last_comments
    UNION ALL
    SELECT * FROM last_errata
    UNION ALL
    SELECT * FROM last_exclusions
    UNION ALL
    SELECT * FROM last_cpes
    UNION ALL
    SELECT * FROM last_pncs
)
ORDER BY date DESC
LIMIT target_limit
"""

    get_user_aliases = """
SELECT
    user,
    argMax(aliases, ts) AS aka
FROM ErrataUsersAliases
{where_clause}
GROUP BY user
{having_clause}
ORDER BY user
"""

    store_user_aliases = """
INSERT INTO ErrataUsersAliases (user, aliases) VALUES
"""

    get_original_user_name = """
SELECT get_errata_user_original_name('{user}')
"""

    get_errata_user_active_subscriptions = """
SELECT
    user,
    entity_type,
    entity_link,
    argMax(state, date) AS last_state,
    argMax(assigner, date),
    max(date) AS last_date
FROM ErrataUsersSubscriptions
WHERE user = '{user}'
GROUP BY
    user,
    entity_type,
    entity_link
HAVING last_state = 'active'
ORDER BY last_date DESC
"""

    get_errata_user_active_subscription = """
SELECT
    user,
    entity_type,
    entity_link,
    argMax(state, date) AS last_state,
    argMax(assigner, date),
    max(date) AS last_date
FROM ErrataUsersSubscriptions
WHERE user = '{user}'
    AND entity_type = '{entity_type}'
    AND entity_link = '{entity_link}'
GROUP BY
    user,
    entity_type,
    entity_link
HAVING last_state = 'active'
"""

    get_entity_subscribed_users = """
SELECT
    user,
    entity_type,
    entity_link,
    argMax(state, date) AS last_state,
    argMax(assigner, date),
    max(date) AS last_date
FROM ErrataUsersSubscriptions
WHERE entity_link = '{entity_link}'
GROUP BY
    user,
    entity_type,
    entity_link
HAVING last_state = 'active'
"""

    store_errata_user_subscription = """
    INSERT INTO ErrataUsersSubscriptions (*) VALUES
"""

    get_errata_user_tracked_entities = """
WITH '{user}' AS target_user,
subscriptions AS (
    SELECT
        user,
        entity_type,
        entity_link,
        argMax(state, date) AS last_state,
        argMax(assigner, date) AS last_assigner,
        max(date) AS last_date
    FROM ErrataUsersSubscriptions
    WHERE user = target_user
    GROUP BY
        user,
        entity_type,
        entity_link
    HAVING last_state = 'active'
),
_last_vuln_status_changes_by_author AS (
    SELECT
        vuln_id,
        vs_author,
        vs_updated
    FROM VulnerabilityStatus
    INNER JOIN
    (
        SELECT DISTINCT
            entity_link AS id,
            last_date AS sub_date
        FROM subscriptions
    ) AS S ON vuln_id = S.id
    WHERE target_user = vs_author AND vs_updated >= sub_date
),
last_vuln_statuses AS (
    SELECT
        'vuln_status' AS type,
        vuln_id AS id,
        'update' AS action,
        '' AS attr_type,
        '' AS attr_link,
        map(
            'text', ((arraySlice(vs_history, arrayFirstIndex(vs -> ((vs.1, vs.2, vs.8) = (R.vuln_id, R.vs_author, R.vs_updated)), vs_history), 2) AS vcs)[1]).5,
            'new', (vcs[1]).3,
            'old', (vcs[2]).3
        ) AS info_json,
        vs_updated AS date
    FROM
    (
        SELECT
            vuln_id,
            arrayReverseSort(vs -> (vs.8), groupUniqArray(tuple(*))) AS vs_history
        FROM VulnerabilityStatus
        WHERE vuln_id IN (
            SELECT vuln_id
            FROM _last_vuln_status_changes_by_author
        )
        GROUP BY vuln_id
    ) AS VulnStatusHistory
    RIGHT JOIN _last_vuln_status_changes_by_author AS R USING (vuln_id)
),
last_vulnerabilities AS (
    SELECT
        'vuln' AS type,
        vuln_id AS id,
        'update' AS action,
        '' AS attr_type,
        '' AS attr_link,
        map('text', vuln_url) AS info_json,
        vuln_modified_date AS date
    FROM Vulnerabilities
    INNER JOIN
    (
        SELECT DISTINCT
            entity_link AS id,
            last_date AS sub_date
        FROM subscriptions
        WHERE entity_type = 'vuln'
    ) AS S ON vuln_id = S.id
    HAVING date >= sub_date
),
last_errata AS (
    -- by vuln subscription
    SELECT
        'errata' AS type,
        errata_id AS id,
        CAST(ec_type, 'String') AS action,
        'package' AS attr_type,
        ec_id AS attr_link,
        map('text', JSONExtractString(ec_reason, 'message')) AS info_json,
        ec_updated AS date
    FROM ErrataHistory
    RIGHT JOIN (
        SELECT
            ec_id,
            ec_type,
            errata_id,
            ec_reason,
            ec_updated
        FROM ErrataChangeHistory
        WHERE startsWith(errata_id, 'ALT-PU')
            {only_manual_ec_clause}
    ) AS R USING (errata_id)
    INNER JOIN (
        SELECT DISTINCT
            entity_link AS id,
            last_date AS sub_date
        FROM subscriptions
        WHERE entity_type = 'vuln'
    ) AS S ON has(
        arrayMap(
            p -> (p.2),
            arrayFilter(
                p -> ((p.1) = 'vuln'),
                arrayZip(eh_references.type, eh_references.link)
            )
        ),
        S.id
    )
    HAVING date >= sub_date

    UNION ALL

    -- by package subscription
    SELECT
        'errata' AS type,
        errata_id AS id,
        CAST(ec_type, 'String') AS action,
        'package' AS attr_type,
        ec_id AS attr_link,
        map('text', JSONExtractString(ec_reason, 'message')) AS info_json,
        ec_updated AS date
    FROM ErrataHistory
    RIGHT JOIN (
        SELECT
            ec_id,
            ec_type,
            errata_id,
            ec_reason,
            ec_updated
        FROM ErrataChangeHistory
        WHERE startsWith(errata_id, 'ALT-PU')
            {only_manual_ec_clause}
    ) AS R USING (errata_id)
    INNER JOIN (
        SELECT DISTINCT
            entity_link AS id,
            last_date AS sub_date
        FROM subscriptions
        WHERE entity_type = 'package'
    ) AS S ON pkg_name = S.id
    HAVING date >= sub_date

    UNION ALL

    -- by errata subscription
    SELECT
        'errata' AS type,
        errata_id AS id,
        CAST(ec_type, 'String') AS action,
        'package' AS attr_type,
        ec_id AS attr_link,
        map('text', JSONExtractString(ec_reason, 'message')) AS info_json,
        ec_updated AS date
    FROM ErrataHistory
    RIGHT JOIN (
        SELECT
            ec_id,
            ec_type,
            errata_id,
            ec_reason,
            ec_updated
        FROM ErrataChangeHistory
        WHERE startsWith(errata_id, 'ALT-PU')
            {only_manual_ec_clause}
    ) AS R USING (errata_id)
    INNER JOIN (
        SELECT DISTINCT
            entity_link AS id,
            last_date AS sub_date
        FROM subscriptions
        WHERE entity_type = 'errata'
    ) AS S ON id = S.id
    HAVING date >= sub_date
),
last_exclusions AS (
    -- by vuln type
    SELECT
        'exclusion' AS type,
        errata_id AS id,
        CAST(ec_type, 'String') AS action,
        JSONExtractString(eh_json, 'type') AS attr_type,
        ec_id AS attr_link,
        map('text', JSONExtractString(eh_json, 'reason')) AS info_json,
        ec_updated AS date
    FROM ErrataHistory
    RIGHT JOIN (
        SELECT
            ec_id,
            ec_type,
            errata_id,
            ec_updated
        FROM ErrataChangeHistory
        WHERE startsWith(errata_id, 'ALT-SA')
            {only_manual_ec_clause}
    ) AS R USING (errata_id)
    INNER JOIN (
        SELECT DISTINCT
            entity_link AS id,
            last_date AS sub_date
        FROM subscriptions
        WHERE entity_type = 'vuln'
    ) AS S ON has(
        arrayMap(
            p -> (p.2),
            arrayFilter(
                p -> ((p.1) = 'vuln'),
                arrayZip(eh_references.type, eh_references.link)
            )
        ),
        S.id
    )
    HAVING date >= sub_date

    UNION ALL

    -- by package subscription
    SELECT
        'exclusion' AS type,
        errata_id AS id,
        CAST(ec_type, 'String') AS action,
        JSONExtractString(eh_json, 'type') AS attr_type,
        ec_id AS attr_link,
        map('text', JSONExtractString(eh_json, 'reason')) AS info_json,
        ec_updated AS date
    FROM ErrataHistory
    RIGHT JOIN (
        SELECT
            ec_id,
            ec_type,
            errata_id,
            ec_updated
        FROM ErrataChangeHistory
        WHERE startsWith(errata_id, 'ALT-SA')
            {only_manual_ec_clause}
    ) AS R USING (errata_id)
    INNER JOIN (
        SELECT DISTINCT
            entity_link AS id,
            last_date AS sub_date
        FROM subscriptions
        WHERE entity_type = 'package'
    ) AS S ON has(
        arrayMap(
            p -> (p.2),
            arrayFilter(
                p -> ((p.1) = 'package'),
                arrayZip(eh_references.type, eh_references.link)
            )
        ),
        S.id
    )
    HAVING date >= sub_date

    UNION ALL

    -- by errata subscription
    SELECT
        'exclusion' AS type,
        errata_id AS id,
        CAST(ec_type, 'String') AS action,
        JSONExtractString(eh_json, 'type') AS attr_type,
        ec_id AS attr_link,
        map('text', JSONExtractString(eh_json, 'reason')) AS info_json,
        ec_updated AS date
    FROM ErrataHistory
    RIGHT JOIN (
        SELECT
            ec_id,
            ec_type,
            errata_id,
            ec_updated
        FROM ErrataChangeHistory
        WHERE startsWith(errata_id, 'ALT-SA')
            {only_manual_ec_clause}
    ) AS R USING (errata_id)
    INNER JOIN (
        SELECT DISTINCT
            entity_link AS id,
            last_date AS sub_date
        FROM subscriptions
        WHERE entity_type = 'errata'
    ) AS S ON id = S.id
    HAVING date >= sub_date
),
last_comments AS (
    SELECT
        'comment' AS type,
        CAST(comment_id, 'String') AS id,
        CAST(cc_action, 'String') AS action,
        comment_entity_type AS attr_type,
        comment_entity_link AS attr_link,
        map('text', comment_text) AS info_json,
        comment_created AS date
    FROM Comments
    RIGHT JOIN (
        SELECT
            comment_id,
            cc_action
        FROM CommentsChangeHistory
        WHERE has(get_errata_user_aliases(target_user), cc_user)
    ) AS R USING (comment_id)
    INNER JOIN (
        SELECT DISTINCT
            entity_type,
            entity_link,
            last_date AS sub_date
        FROM subscriptions
    ) AS S ON (comment_entity_type, comment_entity_link) = (entity_type, entity_link)
    HAVING date >= sub_date
)
SELECT DISTINCT
    type,
    id,
    action,
    attr_type,
    attr_link,
    info_json,
    date,
    count(1) OVER() AS total_count
FROM (
    SELECT * FROM last_vuln_statuses
    UNION ALL
    SELECT * FROM last_vulnerabilities
    UNION ALL
    SELECT * FROM last_errata
    UNION ALL
    SELECT * FROM last_exclusions
    UNION ALL
    SELECT * FROM last_comments
)
{having_clause}
{order_by_clause}
{limit_clause}
{page_clause}
"""

    get_img_files_list = """
SELECT DISTINCT
    img_file,
    count(1) OVER() AS total_count
FROM lv_all_image_packages
{where_clause}
ORDER BY img_file
{limit_clause}
{page_clause}
"""


sql = SQL()
