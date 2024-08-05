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
    src_pkg_av_detections = """
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
    FROM Packages AS P 
    INNER JOIN (
        SELECT DISTINCT
            pkg_hash,
            av_scanner,
            av_type,
            av_issue,
            av_message,
            av_target,
            file_name,
            pkgset_name,
            av_date
        FROM static_last_packages
        INNER JOIN (
            SELECT * FROM AntivirusScanStatus
            {where_clause}
        ) AS AV
        USING (pkgset_name, pkg_name, pkg_version, pkg_release) 
        WHERE pkg_sourcepackage = 1
        UNION ALL
        SELECT DISTINCT
            M.pkg_srcrpm_hash AS pkg_hash,
            av_scanner,
            av_type,
            av_issue,
            av_message,
            av_target,
            file_name,
            pkgset_name,
            av_date,
        FROM (SELECT DISTINCT pkg_srcrpm_hash, pkg_hash FROM Packages) AS M
        INNER JOIN (
            SELECT DISTINCT *
            FROM static_last_packages
            INNER JOIN (
                SELECT * FROM AntivirusScanStatus
                {where_clause}
            ) AS AV
            USING (pkgset_name, pkg_name, pkg_version, pkg_release)
        ) AS AV
        ON M.pkg_srcrpm_hash = AV.pkg_hash
    ) AS AV
    USING pkg_hash
    GROUP BY pkgset_name, pkg_hash, pkg_name, pkg_version, pkg_release, file_name
    """

    get_all_av_issues = """
    SELECT DISTINCT
        av_issue
    FROM AntivirusScanStatus
    ORDER BY av_issue ASC
    """


sql = SQL()
