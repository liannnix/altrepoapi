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

from flask_restx import fields

from .namespace import get_namespace

ns = get_namespace()

bugzilla_info_el_model = ns.model(
    "BugzillaInfoElementModel",
    {
        "id": fields.String(description="bug id"),
        "status": fields.String(description="bug status"),
        "resolution": fields.String(description="bug resolution"),
        "severity": fields.String(description="bug severity"),
        "product": fields.String(description="package name"),
        "component": fields.String(description="branch name"),
        "source_package_name": fields.String(description="source package name"),
        "binary_package_name": fields.String(description="binary package name"),
        "assignee": fields.String(description="bug assigned to"),
        "reporter": fields.String(description="bug registered by"),
        "summary": fields.String(description="bug summary"),
        "updated": fields.String(attribute="ts", description="bug record last changed")
    },
)
bugzilla_info_model = ns.model(
    "BugzillaInfoModel",
    {
        "request_args": fields.Raw(description="request arguments"),
        "length": fields.Integer(description="number of bugs found"),
        "bugs": fields.Nested(
            bugzilla_info_el_model,
            description="bugzilla info",
            as_list=True,
        ),
    },
)
