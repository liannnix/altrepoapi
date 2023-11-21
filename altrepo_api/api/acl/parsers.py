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

from altrepo_api.api.parser import (
    parser,
    branch_name_type,
    acl_group_type,
    pkg_name_list_type,
    maintainer_nick_type,
)


branch = parser.register_item(
    "branch",
    type=branch_name_type,
    required=True,
    help="name of packageset",
    location="args",
)
branch_opt = parser.register_item(
    "branch",
    type=branch_name_type,
    required=False,
    action="split",
    help="name of packageset",
    location="args",
)
acl_group_opt = parser.register_item(
    "name",
    type=acl_group_type,
    required=False,
    help="ACL group name",
    location="args",
)
packages_list = parser.register_item(
    "packages_names",
    type=pkg_name_list_type,
    action="split",
    required=True,
    help="source packages names",
    location="args",
)
acl_nickname = parser.register_item(
    "nickname",
    type=maintainer_nick_type,
    required=True,
    help="ACL member nickname",
    location="args",
)


acl_groups_args = parser.build_parser(branch, acl_group_opt)
acl_maintainer_groups_args = parser.build_parser(branch_opt, acl_nickname)
acl_by_packages_args = parser.build_parser(branch, packages_list)
