# ALTRepo API
# Copyright (C) 2021  BaseALT Ltd

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

    get_all_iso_names = """
SELECT
    pkgset_uuid,
    pkgset_nodename,
    pkgset_date
FROM PackageSetName
WHERE (pkgset_nodename, pkgset_date) IN
(
    SELECT
        argMax(pkgset_name, pkgset_date) AS pkgset_n,
        max(pkgset_date) AS pkgset_d
    FROM StaticLastPackages
    WHERE endsWith(pkgset_name, ':iso')
    GROUP BY pkgset_name
)
    AND pkgset_depth = 0
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

sql = SQL()
