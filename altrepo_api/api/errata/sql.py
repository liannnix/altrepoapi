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
    get_pkg_name_by_srcpkg = """
SELECT DISTINCT pkg_name
FROM Packages
WHERE pkg_srcrpm_hash IN
(
    SELECT pkg_hash FROM {tmp_table}
)
    AND pkg_sourcepackage = 0
    AND pkg_name NOT LIKE '%%-devel'
    AND pkg_name NOT LIKE '%%-debuginfo'
"""

    get_bugzilla_summary_by_ids = """
SELECT
    bz_id,
    argMax(bz_summary, ts),
FROM Bugzilla
WHERE bz_id IN (
    SELECT bz_id FROM {tmp_table}
)
GROUP BY bz_id
"""


sql = SQL()
