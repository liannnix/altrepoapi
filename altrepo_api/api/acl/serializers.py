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

from flask_restx import fields

from .namespace import get_namespace

ns = get_namespace()

acl_groups_el_model = ns.model(
    "AclGroupsElementModel",
    {
        "group": fields.String(description="ACL group name"),
        "date": fields.DateTime(description="ACL group last updated"),
        "maintainers": fields.List(fields.String(description="Maintainer's nicknames")),
    },
)
acl_groups_model = ns.model(
    "AclGroupsModel",
    {
        "request_args": fields.Raw(description="request arguments"),
        "length": fields.Integer(description="number of ACL groups found"),
        "groups": fields.Nested(
            acl_groups_el_model, description="ACL groups list", as_list=True
        ),
    },
)

acl_by_packages_el_model = ns.model(
    "AclByPackagesElementModel",
    {
        "name": fields.String(description="package name"),
        "date": fields.DateTime(description="last ACL update date"),
        "members": fields.List(fields.String(description="members")),
    },
)
acl_by_packages_model = ns.model(
    "AclByPackagesModel",
    {
        "branch": fields.String(description="packages' branch"),
        "packages": fields.Nested(
            acl_by_packages_el_model,
            description="packages with its ACL members",
            as_list=True,
        ),
    },
)
