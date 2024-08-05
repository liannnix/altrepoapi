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

from flask_restx import fields

from .namespace import get_namespace

ns = get_namespace()

avs_object_model = ns.model(
    "AvScannerObjectModel",
    {
        "av_scanner": fields.String(description="Antivirus name"),
        "av_type": fields.String(description="Antivirus detected type"),
        "av_issue": fields.String(description="Antivirus detected issue"),
        "av_message": fields.String(description="Full message for current trigger"),
        "av_target": fields.String(description="Branch or image"),
        "date": fields.DateTime(description="Detection date"),
    },
)
source_pkg_model = ns.model(
    "AvScannerSourcePkgModel",
    {
        "pkgset_name": fields.String(description="Branch name"),
        "pkg_name": fields.String(description="Package source name"),
        "pkg_version": fields.String(description="Package version"),
        "pkg_release": fields.String(description="Package release"),
        "pkg_hash": fields.String(description="Package hash"),
        "fn_name": fields.String(description="File name"),
        "detect_info": fields.Nested(
            avs_object_model,
            description="Antivirus detection information",
            as_list=True,
        ),
    },
)
avs_pkg_list_response_model = ns.model(
    "AvScannerPackagesListResponseModel",
    {
        "length": fields.Integer(
            description="Number of antivirus scanner detected matches found"
        ),
        "detections": fields.Nested(
            source_pkg_model,
            description="List of antivirus detections found",
            as_list=True,
        ),
    },
)
source_issue_model = ns.model(
    "AvScannerIssueModel",
    {
        "av_issue": fields.String(description="Antivirus detected issue"),
    },
)
avs_issue_list_response_model = ns.model(
    "AvScannerIssueListResponseModel",
    {
        "length": fields.Integer(
            description="Number of antivirus issues detected matches found"
        ),
        "issues": fields.Nested(
            source_issue_model,
            description="List of antivirus issues found",
            as_list=True,
        ),
    },
)
