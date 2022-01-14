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

    get_all_pkgset_names = """
SELECT groupUniqArray(pkgset_name)
FROM lv_pkgset_stat
WHERE pkgset_name NOT LIKE '%:%'
"""

    get_all_pkgset_names_with_pkg_count = """
SELECT
    pkgset_name,
    cnt
FROM lv_pkgset_stat
WHERE pkg_arch = 'srpm'
    AND pkgset_name NOT LIKE '%:%'
"""

    get_all_pkgsets_with_src_cnt_by_bin_archs = """
SELECT
    pkgset_name,
    pkg_arch,
    cnt
FROM lv_pkgset_stat
WHERE pkgset_name NOT LIKE '%:%'
"""

    get_pkgset_status = """
SELECT
    pkgset_name,
    argMax(rs_start_date, ts) AS start_date,
    argMax(rs_end_date, ts) AS end_date,
    argMax(rs_show, ts) AS show,
    argMax(rs_description_ru, ts) AS desc_ru,
    argMax(rs_description_en, ts) AS desc_en
FROM RepositoryStatus
GROUP BY pkgset_name
"""

    get_pkgset_groups_count = """
SELECT
    pkg_group_,
    count(pkg_hash)
FROM Packages
WHERE pkg_hash IN
(
    SELECT pkg_hash
    FROM static_last_packages
    WHERE pkgset_name = '{branch}'
        AND pkg_sourcepackage IN {sourcef}
        AND pkg_name NOT LIKE '%%-debuginfo'
)
GROUP BY pkg_group_
ORDER BY pkg_group_ ASC
"""

    get_all_bin_pkg_archs = """
SELECT groupUniqArray(pkg_arch)
FROM lv_pkgset_stat
WHERE pkgset_name = '{branch}'
"""

    get_all_src_cnt_by_bin_archs = """
SELECT
    pkg_arch,
    cnt
FROM lv_pkgset_stat
WHERE pkgset_name = '{branch}'
    AND pkg_arch NOT LIKE 'srpm'
"""


sql = SQL()
