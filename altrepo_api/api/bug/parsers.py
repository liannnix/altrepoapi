# ALTRepo API
# Copyright (C) 2021-2026  BaseALT Ltd

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

from altrepo_api.api.parser import (
    parser,
    pkg_name_type,
    packager_nick_type,
    branch_name_type,
    img_edition_type,
)

by_acl_opt = parser.register_item(
    "by_acl",
    type=str,
    choices=(
        "none",
        "by_nick",
        "by_nick_leader",
        "by_nick_or_group",
        "by_nick_leader_and_group",
    ),
    default="none",
    required=False,
    help="search maintainer's packages by ACL",
    location="args",
)
package_name = parser.register_item(
    "package_name",
    type=pkg_name_type,
    required=True,
    help="source or binary package name",
    location="args",
)
package_type_opt = parser.register_item(
    "package_type",
    type=str,
    choices=("source", "binary"),
    default="source",
    required=False,
    help="packages type [source|binary]",
    location="args",
)
maintainer_nickname = parser.register_item(
    "maintainer_nickname",
    type=packager_nick_type,
    required=True,
    help="maintainer nickname",
    location="args",
)
branch = parser.register_item(
    "branch",
    type=branch_name_type,
    required=True,
    help="name of packageset",
    location="args",
)
img_edition_type = parser.register_item(
    "edition",
    type=img_edition_type,
    required=True,
    help="Image edition",
    location="args",
)

package_bugzilla_args = parser.build_parser(package_name, package_type_opt)
bugzilla_by_edition_args = parser.build_parser(branch, img_edition_type)
maintainer_bugzilla_args = parser.build_parser(maintainer_nickname, by_acl_opt)
