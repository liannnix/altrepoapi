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

    truncate_tmp_table = """
TRUNCATE TABLE {tmp_table}
"""

    drop_tmp_table = """
DROP TABLE {tmp_table}
"""

    get_all_iso_images = """
SELECT DISTINCT
    img_branch,
    img_edition,
    img_tag,
    img_kv['file'],
    pkgset_uuid,
    pkgset_date
FROM ImagePackageSetName
WHERE (pkgset_date, img_tag) IN
    (
        SELECT
            max(pkgset_date) AS img_d,
            argMax(img_tag, pkgset_date) AS img_t
        FROM ImagePackageSetName
        WHERE img_type = 'iso'
        GROUP BY img_tag
    )
"""

    get_img_root_info = """
SELECT DISTINCT
    pkgset_uuid,
    pkgset_date,
    img_tag,
    img_branch,
    img_edition,
    img_flavor,
    img_platform,
    img_release,
    img_version_major,
    img_version_minor,
    img_version_sub,
    img_arch,
    img_variant,
    img_type,
    img_kv
FROM ImagePackageSetName
WHERE (ts, img_tag) IN
    (
        SELECT
            max(ts) AS ts,
            argMax(img_tag, pkgset_date) AS img_t
        FROM ImagePackageSetName
        GROUP BY img_tag
    )
    {image_clause}
"""

    get_iso_image_components = """
SELECT
    pkgset_ruuid,
    pkgset_uuid,
    pkgset_nodename,
    cast(arrayZip(pkgset_kv.k, pkgset_kv.v), 'Map(String,String)')
FROM PackageSetName
WHERE pkgset_depth = 1
    AND pkgset_ruuid IN {ruuids}
ORDER BY pkgset_tag ASC, pkgset_date DESC
"""

    get_all_iso_info = """
WITH
iso_roots AS (
    SELECT
        pkgset_nodename AS name,
        max(pkgset_date) AS date,
        argMax(pkgset_uuid, pkgset_date) AS ruuid
    FROM PackageSetName
    WHERE pkgset_nodename IN
    (
        SELECT DISTINCT pkgset_name
        FROM lv_pkgset_stat
        WHERE endsWith(pkgset_name, ':iso')
            {image_clause}
    ) AND pkgset_depth = 0
    GROUP BY pkgset_nodename
)
SELECT
    pkgset_ruuid,
    pkgset_nodename AS name,
    pkgset_date AS date,
    PSL.depth,
    PSL.uuid,
    PSL.leaf_name,
    PSL.leaf_k,
    PSL.leaf_v
FROM PackageSetName
LEFT JOIN
(
    SELECT
        pkgset_ruuid,
        pkgset_uuid as uuid,
        pkgset_depth AS depth,
        pkgset_nodename AS leaf_name,
        pkgset_kv.k AS leaf_k,
        pkgset_kv.v AS leaf_v
    FROM PackageSetName
    WHERE pkgset_ruuid IN
    (
        SELECT ruuid FROM iso_roots
    )
    {component_clause}
) AS PSL USING pkgset_ruuid
WHERE pkgset_depth = 0
    AND pkgset_ruuid IN
    (
        SELECT ruuid FROM iso_roots
    )
ORDER BY name ASC,  depth ASC, date DESC
"""

    get_pkgs_not_in_db = """
WITH
PkgsInDB AS
(
    SELECT pkg_hash
    FROM Packages
    WHERE pkg_hash IN
    (
        SELECT * FROM {tmp_table}
    )
)
SELECT DISTINCT pkg_hash
FROM {tmp_table}
WHERE pkg_hash NOT IN
(
    SELECT * FROM PkgsInDB
)
"""

    get_pkgs_not_in_branch = """
WITH
PkgsetRoots AS
(
    SELECT pkgset_uuid, pkgset_date
    FROM PackageSetName
    WHERE pkgset_depth = 0
        AND pkgset_nodename = '{branch}'
),
PkgsetUUIDs AS
(
    SELECT pkgset_uuid, R.pkgset_date AS pdate, R.pkgset_uuid AS ruuid
    FROM PackageSetName
    LEFT JOIN
    (
        SELECT pkgset_date, pkgset_uuid FROM PkgsetRoots
    ) AS R ON R.pkgset_uuid = PackageSetName.pkgset_ruuid
    WHERE pkgset_depth = 2
        AND pkgset_ruuid IN
        (
            SELECT pkgset_uuid FROM PkgsetRoots
        )
)
SELECT
    pkg_hash,
    T.cnt
FROM {tmp_table}
LEFT JOIN
(
    SELECT
        pkg_hash AS hash,
        count(pkg_hash) AS cnt
    FROM PackageSet
    WHERE pkg_hash IN (
        SELECT pkg_hash FROM {tmp_table}
    )
        AND pkgset_uuid IN (
            SELECT pkgset_uuid FROM PkgsetUUIDs
        )
    GROUP BY hash
) AS T ON T.hash = pkg_hash
"""

    get_pkgs_tasks = """
SELECT DISTINCT
    arrayJoin(titer_pkgs_hash) AS pkg_hash,
    task_id,
    subtask_id
FROM TaskIterations
WHERE pkg_hash IN {hshs}
"""

    tmp_table_columns = (
        "(pkg_hash UInt64, pkg_name String, pkg_epoch UInt32,"
        "pkg_version String, pkg_release String, pkg_disttag String,"
        "pkg_arch String, pkg_buildtime UInt32)"
    )

    tmp_pkgs_by_nevr = """
CREATE TEMPORARY TABLE {tmp_table} AS
(
    SELECT DISTINCT
        pkg_hash,
        pkg_name,
        pkg_epoch,
        pkg_version,
        pkg_release,
        pkg_disttag,
        pkg_arch,
        pkg_buildtime
    FROM Packages
    WHERE pkg_sourcepackage = 0
        AND (pkg_name, pkg_epoch, pkg_version, pkg_release, pkg_disttag, pkg_arch) IN
        (
            SELECT
                pkg_name,
                pkg_epoch,
                pkg_version,
                pkg_release,
                pkg_disttag,
                pkg_arch
            FROM {tmp_table2}
        )
)
"""

    tmp_pkgs_in_branch = """
CREATE TEMPORARY TABLE {tmp_table} AS
(
    WITH
    HshByNEVR AS
    (
        SELECT DISTINCT
            pkg_hash
        FROM Packages
        WHERE pkg_sourcepackage = 0
            AND (pkg_name, pkg_epoch, pkg_version, pkg_release, pkg_disttag, pkg_arch) IN
            (
                SELECT
                    pkg_name,
                    pkg_epoch,
                    pkg_version,
                    pkg_release,
                    pkg_disttag,
                    pkg_arch
                FROM {tmp_table2}
            )
    ),
    PkgsetRoots AS
    (
        SELECT pkgset_uuid, pkgset_date
        FROM PackageSetName
        WHERE pkgset_depth = 0
            AND pkgset_nodename = '{branch}'
    ),
    PkgsetUUIDs AS
    (
        SELECT pkgset_uuid, R.pkgset_date AS pdate, R.pkgset_uuid AS ruuid
        FROM PackageSetName
        LEFT JOIN
        (
            SELECT pkgset_date, pkgset_uuid FROM PkgsetRoots
        ) AS R ON R.pkgset_uuid = PackageSetName.pkgset_ruuid
        WHERE pkgset_depth = 2
            AND pkgset_ruuid IN
            (
                SELECT pkgset_uuid FROM PkgsetRoots
            )
    ),
    HshInBranch AS
    (
        SELECT pkg_hash
        FROM
        (
            SELECT
                pkg_hash,
                T.cnt
            FROM HshByNEVR
            LEFT JOIN
            (
                SELECT
                    pkg_hash AS hash,
                    count(pkg_hash) AS cnt
                FROM PackageSet
                WHERE pkgset_uuid IN (
                    SELECT pkgset_uuid FROM PkgsetUUIDs
                )
                    AND pkg_hash IN (
                        SELECT pkg_hash FROM HshByNEVR
                    )
                GROUP BY hash
            ) AS T ON T.hash = pkg_hash
        ) WHERE cnt > 0
    )
    SELECT DISTINCT
        pkg_hash,
        pkg_name,
        pkg_epoch,
        pkg_version,
        pkg_release,
        pkg_disttag,
        pkg_arch,
        pkg_buildtime
    FROM Packages
    WHERE pkg_hash IN (SELECT pkg_hash FROM HshInBranch)
        AND (pkg_name, pkg_epoch, pkg_version, pkg_release, pkg_disttag, pkg_arch) IN
        (
            SELECT
                pkg_name,
                pkg_epoch,
                pkg_version,
                pkg_release,
                pkg_disttag,
                pkg_arch
            FROM {tmp_table2}
        )
)
"""

    get_pkgs_tasks_nevr = """
WITH
PkgsByNEVR AS
(
    SELECT DISTINCT
        pkg_hash,
        pkg_name,
        pkg_epoch,
        pkg_version,
        pkg_release,
        pkg_disttag,
        pkg_arch,
        pkg_buildtime
    FROM Packages
    WHERE pkg_sourcepackage = 0
        AND (pkg_name, pkg_epoch, pkg_version, pkg_release, pkg_disttag, pkg_arch) IN
        (
            SELECT
                pkg_name,
                pkg_epoch,
                pkg_version,
                pkg_release,
                pkg_disttag,
                pkg_arch
            FROM {tmp_table}
        )
),
PkgsTasks AS
(
    SELECT DISTINCT
        arrayJoin(titer_pkgs_hash) AS pkg_hash,
        task_id,
        subtask_id
    FROM TaskIterations
    WHERE pkg_hash IN
    (
        SELECT pkg_hash FROM PkgsByNEVR
    )

)
SELECT
    pkg_hash,
    task_id,
    subtask_id,
    P.*
FROM PkgsTasks
LEFT JOIN
(
    SELECT * FROM PkgsByNEVR
) AS P USING pkg_hash
"""

    get_pkgs_last_branch = """
SELECT
    pkg_hash,
    pkg_name,
    pkg_epoch,
    pkg_version,
    pkg_release,
    pkg_disttag,
    pkg_arch,
    pkg_buildtime
FROM last_packages
WHERE pkgset_name = '{branch}'
    AND pkg_sourcepackage = 0
    AND (pkg_name, pkg_epoch, pkg_version, pkg_release, pkg_arch) IN
    {nevra}
"""

    get_pkgs_last_branch_by_na = """
SELECT
    pkg_hash,
    pkg_name,
    pkg_epoch,
    pkg_version,
    pkg_release,
    pkg_disttag,
    pkg_arch,
    pkg_buildtime
FROM last_packages
WHERE pkgset_name = '{branch}'
    AND pkg_sourcepackage = 0
    AND (pkg_name, pkg_arch) IN
    {na}
"""

    insert_image_status = """
INSERT INTO ImageStatus (*) VALUES
"""

    insert_image_tag_status = """
INSERT INTO ImageTagStatus (*) VALUES
"""

    get_img_status = """
SELECT
    img_branch,
    img_edition,
    argMax(img_name, ts) AS img_name,
    argMax(img_show, ts) AS img_show,
    argMax(img_summary_ru, ts) AS img_summary_ru,
    argMax(img_summary_en, ts) AS img_summary_en,
    argMax(img_start_date, ts) AS img_start_date,
    argMax(img_end_date, ts) AS img_end_date,
    argMax(img_description_ru, ts) AS img_description_ru,
    argMax(img_description_en, ts) AS img_description_en,
    argMax(img_mailing_list, ts) AS img_mailing_list,
    argMax(img_name_bugzilla, ts) AS img_name_bugzilla,
    argMax(img_json, ts) AS img_json
FROM ImageStatus
GROUP BY 
    img_branch,
    img_edition
"""

    get_img_tag_status = """
SELECT
    img_tag,
    argMax(img_show, ts) AS img_show
FROM ImageTagStatus
WHERE img_tag IN (
    SELECT img_tag
    FROM ImagePackageSetName
    WHERE img_branch = '{branch}'
        {edition}
)
GROUP BY img_tag
"""

    get_last_image_all_pkg_diff = """
CREATE TEMPORARY TABLE {tmp_table} AS
SELECT pkg_hash FROM
(
    SELECT DISTINCT pkg_hash
        FROM PackageSet
        WHERE pkgset_uuid IN (
            SELECT pkgset_uuid
            FROM PackageSetName
            WHERE pkgset_ruuid = '{uuid}'
            AND pkgset_depth = 1
    )
)    
"""

    get_last_image_cmp_pkg_diff = """
CREATE TEMPORARY TABLE {tmp_table} AS
SELECT pkg_hash FROM
(
    SELECT DISTINCT pkg_hash
        FROM PackageSet
        WHERE pkgset_uuid IN (
            SELECT pkgset_uuid
            FROM PackageSetName
            WHERE pkgset_uuid = '{uuid}'
                AND pkgset_depth = 1
    )
)    
"""

    get_img_pkg_info = """
CREATE TEMPORARY TABLE {tmp_table} AS
SELECT * FROM
(
    SELECT
        pkg_hash,
        pkg_summary,
        pkg_name,
        pkg_arch,
        pkg_version,
        pkg_release
    FROM Packages
    WHERE pkg_hash IN (
        SELECT pkg_hash FROM {tmp_pkg_hashes}
        )
)    
    """

    get_last_image_pkgs_info = """
SELECT
    task_id,
    task_changed,
    tplan_action,
    pkgset_name,
    pkg_hash,
    pkg_name,
    pkg_version,
    pkg_release,
    pkg_arch,
    chlog_date,
    chlog_name,
    chlog_nick,
    chlog_evr,
    chlog_text,
    IMG.pkg_hash,
    IMG.pkg_summary,
    IMG.pkg_version,
    IMG.pkg_release
FROM BranchPackageHistory
LEFT JOIN (
    SELECT DISTINCT *
    FROM {tmp_table}
) AS IMG ON IMG.pkg_name = BranchPackageHistory.pkg_name and IMG.pkg_arch = BranchPackageHistory.pkg_arch
WHERE (pkg_name, pkg_arch) IN (
    SELECT pkg_name, pkg_arch FROM {tmp_table}
    )
    AND (task_id, pkg_name, pkg_arch, tplan_action) IN (
        SELECT
            task_id,
            pkg_name,
            pkg_arch,
            if(has(groupUniqArray(tplan_action), 0), 'add', 'delete') AS actions
        FROM BranchPackageHistory
        WHERE (pkg_name, pkg_arch) IN (
            SELECT pkg_name, pkg_arch FROM {tmp_table}
            )
            AND pkgset_name = '{branch}'
            AND pkg_sourcepackage = 0
        GROUP BY
            task_id,
            pkg_name,
            pkg_arch
    )
    AND pkgset_name = '{branch}'
    AND pkg_sourcepackage = 0
ORDER BY task_changed DESC
LIMIT {limit}
"""

    get_image_uuid_by_tag = """
WITH
root_info AS (
SELECT
    argMax(pkgset_uuid, ts) AS uuid,
    argMax(img_kv['file'], ts) AS r_file,
    argMax(img_type, ts) AS img_type
FROM ImagePackageSetName
WHERE img_tag = '{img_tag}'
)
SELECT
    pkgset_ruuid,
    groupUniqArray(pkgset_nodename),
    any(RI.r_file),
    any(RI.img_type)
FROM PackageSetName
LEFT JOIN
(
    SELECT uuid, r_file, img_type FROM root_info
) AS RI ON RI.uuid = pkgset_ruuid
WHERE pkgset_ruuid IN (SELECT uuid FROM root_info)
    AND pkgset_depth != 0
GROUP BY pkgset_ruuid
"""

    get_image_groups_count = """
SELECT
    pkg_group_,
    count(pkg_hash)
FROM Packages
WHERE pkg_hash IN
(
    SELECT DISTINCT pkg_hash
    FROM PackageSet
    WHERE pkgset_uuid IN (
        SELECT pkgset_uuid
        FROM PackageSetName
        WHERE pkgset_ruuid = '{uuid}'
            {component}
    )
)
AND pkg_name NOT LIKE '%%-debuginfo'
GROUP BY pkg_group_
ORDER BY pkg_group_ ASC    
"""

    get_image_packages = """
WITH
pkg_hashes AS (
    SELECT DISTINCT pkg_hash
    FROM PackageSet
    WHERE pkgset_uuid IN (
        SELECT pkgset_uuid
        FROM PackageSetName
        WHERE pkgset_ruuid = '{uuid}'
        {component}
    )
),
pkg_info AS
(
SELECT
    pkg_hash,
    pkg_changelog.hash[1] AS hash
FROM Packages
WHERE pkg_hash IN (
    SELECT * FROM pkg_hashes
)
    {group}
),
pkg_changelogs AS (
SELECT chlog_hash,
       chlog_text
FROM Changelog
WHERE chlog_hash IN (
    SELECT hash FROM pkg_info
    )
)
SELECT DISTINCT
    pkg_hash,
    pkg_name,
    pkg_version,
    pkg_release,
    pkg_arch,
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
WHERE pkg_hash IN (
    SELECT pkg_hash FROM pkg_info
    )
"""

    get_group_subgroups = """
SELECT DISTINCT pkg_group_
FROM Packages
WHERE pkg_hash IN
(
    SELECT DISTINCT pkg_hash
    FROM PackageSet
    WHERE pkgset_uuid IN (
        SELECT pkgset_uuid
        FROM PackageSetName
        WHERE pkgset_ruuid = '{uuid}'
        {component}
    )
)
    AND pkg_name NOT LIKE '%%-debuginfo'
    AND pkg_group_ like '{group}%%'
    AND pkg_group_ != '{group}'
"""

    get_last_image_packages_with_cve_fixes = """
WITH
pkg_info AS
(
SELECT
    pkg_hash,
    pkg_changelog.hash[1] AS hash
FROM Packages
WHERE pkg_hash IN (
    SELECT DISTINCT pkg_hash
    FROM PackageSet
    WHERE pkgset_uuid IN (
        SELECT pkgset_uuid
        FROM PackageSetName
        WHERE pkgset_ruuid = '{uuid}'
            {component}
    )
)
),
changelog_with_cve AS
(
    SELECT DISTINCT
        chlog_hash,
        chlog_text
    FROM Changelog
    WHERE match(chlog_text, 'CVE-\d{{4}}-(\d{{7}}|\d{{6}}|\d{{5}}|\d{{4}})')
        AND chlog_hash IN (
            SELECT hash FROM pkg_info
        )
)
SELECT
    PKG.*,
    chlog_text
FROM changelog_with_cve
INNER JOIN
(
    SELECT DISTINCT
        pkg_hash,
        TT.pkg_name,
        TT.pkg_version,
        TT.pkg_release,
        TT.pkg_arch,
        TT.pkg_summary,
        TT.pkg_buildtime,
        pkg_changelog.hash[1] AS chlg_hash
    FROM Packages
    LEFT JOIN (
        SELECT
            pkg_hash,
            pkg_name,
            pkg_version,
            pkg_release,
            pkg_arch,
            pkg_summary,
            pkg_buildtime
        FROM Packages
        ) AS TT ON TT.pkg_hash = Packages.pkg_hash
    WHERE pkg_hash IN (
        SELECT pkg_hash FROM pkg_info
    )
) AS PKG ON PKG.chlg_hash = changelog_with_cve.chlog_hash
"""

    get_active_images = """
WITH editions_status AS (
    SELECT img_edition,
           argMax(img_show, ts) AS edition_show
    FROM ImageStatus
    GROUP BY img_edition
),
tags_status AS (
    SELECT img_tag,
           argMax(img_show, ts) AS tag_show
    FROM ImageTagStatus
    GROUP BY img_tag
)
SELECT DISTINCT
    img_edition,
    groupUniqArray(TT.img_tag) as tags
FROM ImagePackageSetName
LEFT JOIN (
    SELECT img_edition, img_tag
    FROM ImagePackageSetName
    WHERE img_tag IN (select img_tag FROM tags_status WHERE tag_show = 'show')
    {image_clause}
    GROUP BY img_edition, img_tag
) AS TT ON TT.img_edition = ImagePackageSetName.img_edition
WHERE img_edition IN (select img_edition FROM editions_status WHERE edition_show = 'show')
    AND img_branch = '{branch}'
GROUP BY img_edition
ORDER BY tags ASC, img_edition ASC
"""


sql = SQL()
