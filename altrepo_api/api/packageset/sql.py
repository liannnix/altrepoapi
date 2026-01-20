# ALTRepo API
# Copyright (C) 2021-2026  BaseALT Ltd

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
    get_repo_packages = """
SELECT
    pkg_hash,
    pkg_name,
    pkg_version,
    pkg_release,
    pkg_summary,
    groupUniqArray(pkg_packager_email) AS packagers,
    pkg_url,
    pkg_license,
    pkg_group_,
    groupUniqArray(pkg_arch),
    acl_list
FROM last_packages
LEFT JOIN
(
    SELECT
        acl_for AS pkg_name,
        acl_list
    FROM last_acl
    WHERE acl_branch = '{branch}'
) AS Acl USING pkg_name
WHERE pkgset_name = '{branch}'
    AND pkg_sourcepackage IN {src}
    {archs}
    AND pkg_name NOT LIKE '%%-debuginfo'
GROUP BY
    pkg_hash,
    pkg_name,
    pkg_version,
    pkg_release,
    pkg_summary,
    pkg_url,
    pkg_license,
    pkg_group_,
    acl_list
ORDER BY pkg_name
"""

    get_compare_info = """
SELECT
    pkg_name,
    pkg_version,
    pkg_release,
    Df.pkg_name,
    Df.pkg_version,
    Df.pkg_release
FROM
(
    SELECT
        pkg_name,
        pkg_version,
        pkg_release
    FROM static_last_packages
    WHERE pkgset_name = %(pkgset1)s
        AND pkg_sourcepackage = 1
        AND
        (
            pkg_name,
            pkg_version,
            pkg_release
        ) NOT IN
        (
            SELECT
                pkg_name,
                pkg_version,
                pkg_release
            FROM static_last_packages
            WHERE pkgset_name = %(pkgset2)s
                AND pkg_sourcepackage = 1
        )
        AND pkg_name IN
        (
            SELECT pkg_name
            FROM static_last_packages
            WHERE pkgset_name = %(pkgset2)s
                AND pkg_sourcepackage = 1
        )
) AS PkgSet2
INNER JOIN
(
    SELECT
        pkg_name,
        pkg_version,
        pkg_release
    FROM static_last_packages
    WHERE pkgset_name = %(pkgset2)s
        AND pkg_sourcepackage = 1
) AS Df USING pkg_name
UNION ALL
SELECT
    pkg_name,
    pkg_version,
    pkg_release,
    '',
    '',
    ''
FROM static_last_packages
WHERE pkgset_name = %(pkgset1)s
    AND pkg_sourcepackage = 1
    AND pkg_name NOT IN
    (
        SELECT pkg_name
        FROM static_last_packages
        WHERE pkgset_name = %(pkgset2)s
            AND pkg_sourcepackage = 1
    )
"""

    insert_pkgset_status = """
INSERT INTO RepositoryStatus (*) VALUES
"""

    get_pkgset_status = """
SELECT
    pkgset_name,
    argMax(rs_pkgset_name_bugzilla, ts) AS pkgset_name_bugzilla,
    argMax(rs_start_date, ts) AS start_date,
    argMax(rs_end_date, ts) AS end_date,
    argMax(rs_show, ts) AS show,
    argMax(rs_description_ru, ts) AS desc_ru,
    argMax(rs_description_en, ts) AS desc_en,
    argMax(rs_mailing_list, ts) AS mailing_list,
    argMax(rs_mirrors_json, ts) AS mirrors_json
FROM RepositoryStatus
GROUP BY pkgset_name
"""

    get_active_pkgsets = """
SELECT pkgset_name
FROM
(
    SELECT
        pkgset_name,
        argMax(rs_show, ts) AS show
    FROM RepositoryStatus
    GROUP BY pkgset_name
)
WHERE show = 1
"""

    get_branch_has_active_images = """
SELECT img_branch, count(img_edition)
FROM (
    SELECT
        img_branch,
        img_edition,
        argMax(img_show, ts) AS img_show
    FROM ImageStatus
    GROUP BY
        img_branch,
        img_edition
)
WHERE img_show == 'show'
GROUP BY img_branch
"""

    get_repository_statistics = """
SELECT branch, branch_date, stats
FROM lv_repository_statistics
{branch}
"""

    get_packages_by_uuid = """
WITH
pkg_hashes AS (
    SELECT pkg_hash
    FROM Packages
    WHERE pkg_hash IN (
        select pkg_hash
        FROM PackageSet
        WHERE pkgset_uuid = '{uuid}'
    )
),
pkg_changelogs AS (
    SELECT
        chlog_hash,
        chlog_text
    FROM Changelog
    WHERE chlog_hash IN (
        SELECT pkg_changelog.hash[1] AS hash
        FROM Packages
        WHERE pkg_hash IN (SELECT * FROM pkg_hashes)
    )
)
SELECT DISTINCT
    pkg_hash,
    pkg_name,
    pkg_version,
    pkg_release,
    pkg_arch,
    if(pkg_sourcepackage = 1, 'source', 'binary') as sourcerpm,
    pkg_summary,
    pkg_buildtime,
    pkg_changelog.date[1] AS date,
    pkg_changelog.name[1] as name,
    pkg_changelog.evr[1] AS evr,
    CHLG.chlog_text
FROM Packages
LEFT JOIN (
    SELECT * FROM pkg_changelogs
) AS CHLG ON CHLG.chlog_hash = pkg_changelog.hash[1]
WHERE pkg_hash IN (SELECT pkg_hash FROM pkg_hashes)
"""

    get_done_tasks_after_last_repo = """
WITH
(
    SELECT max(pkgset_date)
    FROM static_last_packages
    WHERE pkgset_name = '{branch}'
) AS last_repo_date,
(
    SELECT toUInt32(pkgset_kv.v[indexOf(pkgset_kv.k, 'task')])
    FROM PackageSetName
    WHERE pkgset_nodename = '{branch}' AND pkgset_date = last_repo_date
) AS last_repo_task,
(
    SELECT max(task_changed)
    FROM TaskStates
    WHERE (task_state = 'DONE') AND task_id = last_repo_task
) AS last_repo_task_changed
SELECT task_id
FROM TaskStates
WHERE task_state = 'DONE'
    AND task_changed > last_repo_task_changed
    AND task_id IN (SELECT task_id FROM Tasks WHERE task_repo = '{branch}')
ORDER BY task_changed DESC
"""

    get_task_plan_hashes = """
SELECT DISTINCT pkgh_mmh
FROM PackageHash
WHERE pkgh_sha256 IN
(
    SELECT tplan_sha256
    FROM TaskPlanPkgHash
    WHERE tplan_hash IN
    (
        SELECT tplan_hash
        FROM task_plan_hashes
        WHERE task_id IN {task_ids}
    )
    AND tplan_action = '{action}'
)
"""

    get_packages_by_tmp_table = """
SELECT
    pkg_hash,
    pkg_name,
    pkg_version,
    pkg_release,
    pkg_summary,
    groupUniqArray(pkg_packager_email) AS packagers,
    pkg_url,
    pkg_license,
    pkg_group_,
    groupUniqArray(pkg_arch),
    Acl.acl_list
FROM Packages
LEFT JOIN
(
    SELECT
        acl_for AS pkg_name,
        acl_list
    FROM last_acl
    WHERE acl_branch = '{branch}'
) AS Acl USING pkg_name
WHERE pkg_hash IN {table}
    AND pkg_sourcepackage IN {src}
    {archs}
    AND pkg_name NOT LIKE '%%-debuginfo'
GROUP BY
    pkg_hash,
    pkg_name,
    pkg_version,
    pkg_release,
    pkg_summary,
    pkg_url,
    pkg_license,
    pkg_group_,
    Acl.acl_list
ORDER BY pkg_name
"""

    get_maintainer_scores_batch = """
WITH
%(half_life_days)s AS half_life_days,
%(w_update)s AS w_update,
%(w_patch)s AS w_patch,
%(w_nmu)s AS w_nmu,
%(acl_non_member_factor)s AS acl_non_member_factor,
%(recent_period_days)s AS recent_period_days,

package_scores AS (
    SELECT
        p.pkg_name AS pkg_name,
        extract(p.pkg_changelog.name, '<(.*)@') AS nick,
        p.pkg_changelog.date AS chlog_date,
        extractAll(p.pkg_changelog.evr, '-alt(.+)$')[1] AS rel,
        multiIf(
            positionCaseInsensitive(c.chlog_text, 'NMU') > 0, 1,
            positionCaseInsensitive(c.chlog_text, 'rebuild') > 0, 1,
            positionCaseInsensitive(c.chlog_text, 'non-maintainer') > 0, 1,
            0
        ) AS has_nmu_text,
        if(%(branch)s = 'sisyphus',
            has(a.acl_list, extract(p.pkg_changelog.name, '<(.*)@')),
            0
        ) AS is_in_acl,
        dateDiff('day', p.pkg_changelog.date, now()) AS age_days
    FROM Packages p
    ARRAY JOIN p.pkg_changelog
    LEFT JOIN Changelog c ON c.chlog_hash = p.pkg_changelog.hash
    LEFT JOIN last_acl a ON a.acl_for = p.pkg_name AND a.acl_branch = 'sisyphus'
    WHERE p.pkg_hash IN (
        SELECT pkg_hash
        FROM last_packages
        WHERE pkgset_name = %(branch)s
            AND pkg_sourcepackage = 1
    )
)

SELECT
    pkg_name,
    nick,
    round(sum(
        multiIf(
            has_nmu_text = 1 AND is_in_acl = 0, w_nmu,
            rel = '1' OR startsWith(rel, '0.'), w_update,
            w_patch
        )
        * exp(-age_days * log(2) / half_life_days)
        * if(is_in_acl, 1.0, acl_non_member_factor)
    ), 2) AS score,
    countIf(rel = '1' OR startsWith(rel, '0.')) AS updates,
    countIf(
        NOT (rel = '1' OR startsWith(rel, '0.'))
        AND NOT (has_nmu_text = 1 AND is_in_acl = 0)
    ) AS patches,
    countIf(has_nmu_text = 1 AND is_in_acl = 0) AS nmu_count,
    any(is_in_acl) AS in_acl,
    max(chlog_date) AS last_activity,
    countIf(age_days <= recent_period_days) AS recent_commits
FROM package_scores
WHERE nick != ''
GROUP BY pkg_name, nick
ORDER BY pkg_name, score DESC
"""

    get_maintainer_bugfixes_batch = """
WITH
%(half_life_days)s AS half_life_days,
%(w_bugfix)s AS w_bugfix,
%(recent_period_days)s AS recent_period_days

SELECT
    bp.src_name AS pkg_name,
    extractAll(bz.bz_assignee, '^([^@]+)')[1] AS nick,
    sum(
        w_bugfix * exp(-dateDiff('day', bz.bz_last_changed, now()) * log(2) / half_life_days)
    ) AS bugfix_score,
    count() AS bugfix_count,
    countIf(dateDiff('day', bz.bz_last_changed, now()) <= recent_period_days) AS recent_bugfixes
FROM Bugzilla bz
INNER JOIN (
    SELECT DISTINCT
        pkg_name AS bin_name,
        replaceRegexpOne(pkg_sourcerpm, '-[^-]+-[^-]+$', '') AS src_name
    FROM last_packages
    WHERE pkgset_name = %(branch)s
        AND pkg_sourcepackage = 0
    UNION ALL
    SELECT DISTINCT
        pkg_name AS bin_name,
        pkg_name AS src_name
    FROM last_packages
    WHERE pkgset_name = %(branch)s
        AND pkg_sourcepackage = 1
) AS bp ON bz.bz_component = bp.bin_name
WHERE bz.bz_status IN ('RESOLVED', 'CLOSED')
    AND bz.bz_resolution = 'FIXED'
    AND extractAll(bz.bz_assignee, '^([^@]+)')[1] != ''
GROUP BY pkg_name, nick
"""


sql = SQL()
