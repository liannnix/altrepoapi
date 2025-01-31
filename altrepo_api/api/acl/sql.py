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
    create_tmp_table = """
CREATE TEMPORARY TABLE {tmp_table} {columns}
"""

    select_all_tmp_table = """
SELECT * FROM {tmp_table}
"""

    insert_into_tmp_table = """
INSERT INTO {tmp_table} (*) VALUES
"""

    get_all_acl_groups = """
SELECT
    acl_for,
    argMax(acl_list, acl_date),
    max(acl_date)
FROM Acl
WHERE acl_branch = '{branch}'
    AND acl_for LIKE '@%'
GROUP BY acl_for
"""

    get_acl_group = """
SELECT
    acl_for,
    argMax(acl_list, acl_date),
    max(acl_date)
FROM Acl
WHERE acl_branch = '{branch}'
    AND acl_for = '@{acl_group}'
GROUP BY acl_for
"""

    get_acl_by_packages = """
SELECT
    argMax(acl_for, acl_date),
    max(acl_date),
    argMax(acl_list, acl_date)
FROM Acl
WHERE (acl_branch = '{branch}')
    AND (acl_for IN (SELECT pkg_name FROM {tmp_table}))
GROUP BY
    acl_for,
    acl_branch
"""

    get_groups_by_nickname = """
SELECT DISTINCT
    acl_branch,
    groupArray(acl_for) AS acl_groups
FROM last_acl
ARRAY JOIN acl_list
WHERE (acl_for LIKE '@%')
    AND (acl_list = '{nickname}')
    {branches_clause}
GROUP BY
    acl_branch
"""


sql = SQL()
