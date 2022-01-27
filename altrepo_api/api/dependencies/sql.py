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

    insert_into_tmp_table = """
INSERT INTO {tmp_table} (*) VALUES
"""

    select_all_tmp_table = """
SELECT * FROM {tmp_table}
"""

    truncate_tmp_table = """
TRUNCATE TABLE {tmp_table}
"""

    drop_tmp_table = """
DROP TABLE {tmp_table}
"""

    get_pkg_binary_versions = """
SELECT DISTINCT
    pkgset_name,
    pkg_version,
    pkg_release,
    toString(pkg_hash)
FROM last_packages
WHERE pkg_name = '{name}'
    AND pkg_arch = '{arch}'
    AND pkg_sourcepackage = 0
"""

    get_depends_bin_pkg = """
SELECT
    dp_name,
    dp_version,
    dp_flag,
    dp_type
FROM Depends
WHERE pkg_hash = {pkghash}
"""

    make_src_depends_tmp = """
CREATE TEMPORARY TABLE {tmp_table} AS
SELECT
    dp_name,
    dp_version,
    dp_flag
FROM Depends
WHERE pkg_hash = {pkghash}
    AND dp_type = 'require'
"""

    make_src_by_bin_deps_tmp = """
CREATE TEMPORARY TABLE {tmp_table_2} AS
SELECT DISTINCT
    pkg_hash
FROM static_last_packages
WHERE pkg_sourcepackage = 1
    AND pkgset_name = '{branch}'
    AND pkg_hash IN
    (
        SELECT pkg_srcrpm_hash
        FROM Packages
        WHERE pkg_hash IN
        (
            SELECT pkg_hash
            FROM Depends
            WHERE dp_type = 'provide'
                AND dp_name IN
                (SELECT dp_name FROM {tmp_table})
        )
    )
"""

    get_src_by_bin_deps = """
SELECT DISTINCT
    pkg_hash,
    pkg_name,
    pkg_version,
    pkg_release,
    pkg_summary
FROM Packages
WHERE pkg_sourcepackage = 1
    AND pkg_hash IN
        (SELECT pkg_hash FROM {tmp_table})
"""

    get_pkgs_name_and_arch = """
SELECT
    pkg_name,
    pkg_arch
FROM Packages
WHERE pkg_hash = {pkghash}
"""

    get_pkg_info = """
SELECT
    pkg_name,
    pkg_epoch,
    pkg_version,
    pkg_release,
    pkg_buildtime
FROM Packages
WHERE pkg_hash = {pkghash}
"""

    get_pkgs_depends = """
SELECT pkg_hash
FROM last_depends
WHERE dp_name = '{dp_name}'
    AND pkgset_name = '{branch}'
    AND dp_type = '{dp_type}'
"""

    get_repo_packages = """
SELECT DISTINCT
    toString(pkg_hash),
    pkg_name,
    pkg_version,
    pkg_release,
    pkg_arch,
    pkg_sourcepackage,
    pkg_buildtime,
    pkg_summary,
    pkg_packager_email,
    pkg_group_
FROM last_packages
WHERE pkgset_name = '{branch}'
    AND pkg_hash IN (SELECT * FROM {tmp_table})
    AND pkg_buildtime >= 0
ORDER BY pkg_name
"""

    get_pkgset_depends = """
SELECT
    count(pkg_hash),
    pkgset_name
FROM last_depends
WHERE dp_name = '{dp_name}'
    AND dp_type = '{dp_type}'
group by pkgset_name
"""


sql = SQL()
