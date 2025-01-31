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

    truncate_tmp_table = """
TRUNCATE TABLE {tmp_table}
"""

    drop_tmp_table = """
DROP TABLE {tmp_table}
"""

    get_aliases = """
SELECT
    alias,
    spdx_id
FROM LicenseAliases
"""

    get_spdx_ids = """
SELECT DISTINCT spdx_id FROM SPDXLicenses
"""

    get_license_info = """
SELECT
    spdx_id,
    spdx_name,
    spdx_text,
    spdx_header,
    spdx_urls,
    spdx_type
FROM SPDXLicenses
WHERE spdx_id = '{id}'
"""


sql = SQL()
