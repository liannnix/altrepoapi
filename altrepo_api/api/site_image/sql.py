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

    get_pkgs_versions_from_images = """
WITH
-- 'p9:alt-workstation:%:iso' AS taglike,
img_uuids AS (
    SELECT
        pkgset_uuid,
        pkgset_ruuid
    FROM PackageSetName
    WHERE pkgset_depth = 1
        AND pkgset_ruuid IN (
            SELECT ruuid FROM (
                SELECT
                    argMax(pkgset_uuid, ts) AS ruuid,
                    img_tag
                FROM ImagePackageSetName
                WHERE img_branch = '{branch}'
                    AND img_edition = '{edition}'
                    AND img_type = '{img_type}'
                    AND img_tag IN (
                        SELECT argMax(img_tag, ts)
                        FROM ImageTagStatus
                        WHERE img_tag LIKE '{taglike}'
                            AND img_show = 1
                        GROUP BY img_tag
                    )
                GROUP BY img_tag
            )
        )
),
img_packages AS (
    SELECT
        any(pkg_hash) AS hash,
        any(pkgset_uuid) AS uuid,
        RUUID.pkgset_ruuid AS ruuid
    FROM PackageSet
    LEFT JOIN
    (
        SELECT * FROM img_uuids
    ) AS RUUID USING pkgset_uuid
    WHERE pkgset_uuid IN (
        SELECT pkgset_uuid FROM img_uuids
    ) AND pkg_hash IN (
        SELECT pkg_hash
        FROM Packages
        WHERE pkg_name = '{name}'
            AND pkg_sourcepackage = 0
    )
    GROUP BY ruuid
)
SELECT
    PKGS.*,
    TAGS.img_tag,
    TAGS.img_platform,
    TAGS.img_version_major,
    TAGS.img_version_minor,
    TAGS.img_version_sub,
    TAGS.img_arch,
    TAGS.img_type
FROM
(
    SELECT
        pkg_hash,
        pkg_name,
        pkg_version,
        pkg_release,
        pkg_arch,
        UUIDS.ruuid
    FROM Packages
    LEFT JOIN
    (
        SELECT hash, ruuid FROM img_packages
    ) AS UUIDS ON UUIDS.hash = Packages.pkg_hash
    WHERE pkg_hash IN (SELECT hash FROM img_packages)
) AS PKGS
LEFT JOIN
(
    SELECT
        img_tag,
        pkgset_uuid,
        img_platform,
        img_version_major,
        img_version_minor,
        img_version_sub,
        img_arch,
        img_type
    FROM ImagePackageSetName
) AS TAGS ON TAGS.pkgset_uuid = PKGS.ruuid
"""


sql = SQL()
