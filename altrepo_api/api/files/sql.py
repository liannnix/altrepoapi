# ALTRepo API
# Copyright (C) 2021-2023  BaseALT Ltd

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

    find_files = """
SELECT 
    splitByChar('|', search_string)[2] as fn_name, 
    lead,
    murmurHash3_64(fn_name) as fn_hash
FROM (
    SELECT argMax(lead, ts) as lead,
           search_string
    FROM FileSearch
    WHERE search_string ILIKE '{branch}|%{input}%|%|binary|%'
    GROUP BY search_string
    {limit}
)
"""

    fast_find_files = """
SELECT DISTINCT splitByChar('|', search_string)[2] as fn_name
FROM FileSearch
WHERE search_string ILIKE '{branch}|%{input}%|%|binary|%'
{limit}
"""

    get_files_info = """
SELECT DISTINCT
    TT.fn_name,
    file_hashname,
    file_class,
    file_linkto,
    file_mode
FROM Files
LEFT JOIN (
    SELECT fn_name, fn_hash FROM {tmp_table}
) AS TT ON TT.fn_hash = file_hashname
WHERE (file_hashname, pkg_hash) IN (
    SELECT fn_hash, lead FROM {tmp_table}
)
"""

    find_pkg_hshs_by_file = """
SELECT argMax(lead, ts) as lead
FROM FileSearch
WHERE search_string ILIKE '{branch}|{file_name}|%|binary|%'
GROUP BY search_string
"""

    get_packages = """
SELECT DISTINCT
    toString(pkg_hash),
    pkg_name,
    pkg_version,
    pkg_release,
    pkg_arch
FROM last_packages
WHERE pkgset_name = '{branch}'
    AND pkg_hash IN (SELECT * FROM {tmp_table})
    AND pkg_buildtime >= 0
    AND pkg_sourcepackage = 0
ORDER BY pkg_name    
"""


sql = SQL()
