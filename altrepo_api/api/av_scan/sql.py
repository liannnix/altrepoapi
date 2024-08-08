# ALTRepo API
# Copyright (C) 2024 BaseALT Ltd

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
    src_av_detections = """
WITH
last_av_logs AS (
    SELECT
        av_scanner,
        pkgset_name,
        max(av_date) AS last_log_date
    FROM AntivirusScanStatus
    GROUP BY (av_scanner, pkgset_name)
),
last_av_results AS (
    SELECT
        av_scanner,
        av_type,
        av_issue,
        av_message,
        av_target,
        file_name,
        pkgset_name,
        pkg_name,
        pkg_version,
        pkg_release,
        pkg_arch,
        av_date
    FROM AntivirusScanStatus
    WHERE (av_scanner, pkgset_name, av_date) IN last_av_logs
    {where_clause}
),
last_pkgs_info AS (
    SELECT DISTINCT
        pkg_hash,
        pkg_name,
        pkg_version,
        pkg_release,
        pkgset_name,
        pkg_sourcepackage
    FROM static_last_packages
    WHERE (pkgset_name, pkg_name) IN (
        SELECT DISTINCT pkgset_name, pkg_name FROM last_av_results
    )
),
src_packages_issues AS (
    SELECT * FROM (
        SELECT (* EXCEPT pkg_sourcepackage)
        FROM last_pkgs_info WHERE pkg_sourcepackage = 1
    ) AS PI
    INNER JOIN (
        SELECT (* EXCEPT pkg_arch)
        FROM last_av_results
        WHERE pkg_arch = 'src'
    ) AS AVI
    USING (pkgset_name, pkg_name, pkg_version, pkg_release)
),
bin_packages_issues AS (
    SELECT * FROM (
        SELECT (* EXCEPT pkg_sourcepackage)
        FROM last_pkgs_info WHERE pkg_sourcepackage = 0
    ) AS PI
    INNER JOIN (
        SELECT (* EXCEPT pkg_arch)
        FROM last_av_results
        WHERE pkg_arch != 'src'
    ) AS AVI
    USING (pkgset_name, pkg_name, pkg_version, pkg_release)
),
bin_src_hashes AS (
    SELECT
        pkg_srcrpm_hash, pkg_hash
    FROM Packages
    WHERE pkg_hash IN (
        SELECT pkg_hash FROM last_pkgs_info WHERE pkg_sourcepackage = 0
    )
),
src_by_bins_issues AS (
    SELECT
        pkgset_name,
        PI.pkg_name,
        PI.pkg_version,
        PI.pkg_release,
        PI.pkg_hash,
        av_scanner,
        av_type,
        av_issue,
        av_message,
        av_target,
        file_name,
        av_date
    FROM Packages AS PI
    INNER JOIN (
        SELECT * FROM bin_packages_issues
        INNER JOIN bin_src_hashes
        USING pkg_hash
    ) AS BPI
    ON PI.pkg_hash = BPI.pkg_srcrpm_hash
)
SELECT
    pkgset_name,
    pkg_hash,
    pkg_name,
    pkg_version,
    pkg_release,
    file_name,
    groupUniqArray(
        (
            av_scanner,
            av_type,
            av_issue,
            av_message,
            av_target,
            av_date
        )
    )
FROM (
    SELECT * FROM src_packages_issues
    UNION ALL
    SELECT * FROM src_by_bins_issues
)
GROUP BY pkgset_name, pkg_hash, pkg_name, pkg_version, pkg_release, file_name
"""

    get_all_av_issues = """
WITH last_av_results AS (
    SELECT
        av_scanner,
        pkgset_name,
        max(av_date) AS last_log_date
    FROM AntivirusScanStatus
    GROUP BY (av_scanner, pkgset_name)
)
SELECT DISTINCT
    av_scanner,
    av_issue,
    av_type
FROM AntivirusScanStatus
WHERE (av_scanner, pkgset_name, av_date) IN last_av_results
{where_clause}
ORDER BY av_scanner, av_type, av_issue
"""


sql = SQL()
