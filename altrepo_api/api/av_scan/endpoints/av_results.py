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

from datetime import datetime
from typing import Any, NamedTuple, Union

from altrepo_api.api.base import APIWorker
from altrepo_api.libs.pagination import Paginator
from altrepo_api.libs.sorting import rich_sort
from altrepo_api.api.misc import lut

from ..sql import sql


class AVScanArgs(NamedTuple):
    input: Union[str, None]
    limit: Union[int, None]
    page: Union[int, None]
    sort: Union[list[str], None]
    branch: Union[str, None]
    scanner: Union[str, None]
    issue: Union[str, None]


class DetectInfo(NamedTuple):
    av_scanner: str
    av_type: str
    av_issue: str
    av_message: str
    av_target: str
    av_date: datetime


class AVScanListResponse(NamedTuple):
    pkgset_name: str
    pkg_name: str
    pkg_version: str
    pkg_release: str
    pkg_hash: str
    file_name: str
    detect_info: list[DetectInfo]

    def asdict(self) -> dict[str, Any]:
        return {
            "pkgset_name": self.pkgset_name,
            "pkg_name": self.pkg_name,
            "pkg_version": self.pkg_version,
            "pkg_release": self.pkg_release,
            "pkg_hash": self.pkg_hash,
            "file_name": self.file_name,
            "detect_info": [el._asdict() for el in self.detect_info],
        }


class AntivirusScanResults(APIWorker):
    """
    Get a list of all Antivirus detected errors from the database.
    """

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args: AVScanArgs = AVScanArgs(**kwargs)
        self.sql = sql
        super().__init__()

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        if self.args.branch and self.args.branch not in lut.av_supported_branches:
            self.validation_results.append(
                f"unknown package set name : {self.args.branch}"
            )

        if self.validation_results != []:
            return False

        return True

    @property
    def _where_params(self) -> str:
        conditions = []

        if self.args.branch:
            conditions.append(f"pkgset_name = '{self.args.branch}'")
        if self.args.scanner and self.args.scanner != "all":
            conditions.append(f"av_scanner = '{self.args.scanner}'")
        if self.args.issue:
            conditions.append(f"av_issue = '{self.args.issue}'")
        if self.args.input:
            conditions.append(
                f"(pkg_name ILIKE '%{self.args.input}%' OR av_message ILIKE '%{self.args.input}%')"
            )

        if conditions:
            where_clause = (
                "WHERE av_target='branch' AND pkg_arch='src' AND "
                + " AND ".join(conditions)
            )
        else:
            where_clause = "WHERE av_target='branch' AND pkg_arch='src'"

        return where_clause

    def _get(self, sql: str):
        limit = self.args.limit
        response = self.send_sql_request(sql.format(where_clause=self._where_params))
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {"message": "No data not found in database"},
            )

        res = [
            AVScanListResponse(
                pkgset_name=pkgset_name,
                pkg_name=pkg_name,
                pkg_version=pkg_version,
                pkg_release=pkg_release,
                pkg_hash=pkg_hash,
                file_name=file_name,
                detect_info=[DetectInfo(*r) for r in reports],
            ).asdict()
            for pkgset_name, pkg_hash, pkg_name, pkg_version, pkg_release, file_name, reports in response
        ]

        if self.args.sort:
            res = rich_sort(res, self.args.sort)

        paginator = Paginator(list(res), limit)
        page_obj = paginator.get_page(self.args.page)

        res = {
            "length": len(page_obj),
            "detections": page_obj,
        }

        return (
            res,
            200,
            {
                "Access-Control-Expose-Headers": "X-Total-Count",
                "X-Total-Count": int(paginator.count),
            },
        )

    def get(self):
        return self._get(self.sql.src_pkg_av_detections)

    def get_images(self):
        return self._get(self.sql.img_av_detections)


class AntivirusScanIssueList(APIWorker):
    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def get(self):
        response = self.send_sql_request(self.sql.get_all_av_issues)
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {"message": "No data not found in database"},
            )

        issues = [{"av_issue": issue[0]} for issue in response]

        res = {
            "length": len(issues),
            "issues": issues,
        }
        return (
            res,
            200,
            {
                "Access-Control-Expose-Headers": "X-Total-Count",
                "X-Total-Count": len(issues),
            },
        )
