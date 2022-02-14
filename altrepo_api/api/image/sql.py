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

    get_iso_root_info = """
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
WHERE (pkgset_date, img_tag) IN
    (
        SELECT
            max(pkgset_date) AS img_d,
            argMax(img_tag, pkgset_date) AS img_t
        FROM ImagePackageSetName
        WHERE img_type = 'iso'
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
    {component_clause}
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


sql = SQL()
