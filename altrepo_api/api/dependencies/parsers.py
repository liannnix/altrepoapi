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
    dp_name_type,
    pkg_name_list_type,
    arch_name_type,
)

branch = parser.register_item(
    "branch",
    type=branch_name_type,
    required=True,
    help="packageset name",
    location="args",
)
dp_name = parser.register_item(
    "dp_name", type=dp_name_type, required=True, help="dependency name", location="args"
)
dp_type_opt = parser.register_item(
    "dp_type",
    type=str,
    choices=("provide", "require", "conflict", "obsolete"),
    default="provide",
    required=False,
    help="type of dependency [provide|require|conflict|obsolete]",
    location="args",
)
depends_depth_opt = parser.register_item(
    "depth",
    type=int,
    default=1,
    required=False,
    help="dependency level limit",
    location="args",
)
branch_from = parser.register_item(
    "from_branch",
    type=branch_name_type,
    required=True,
    help="packageset name where are packages backported from",
    location="args",
)
branch_to = parser.register_item(
    "into_branch",
    type=branch_name_type,
    required=True,
    help="packageset name where are packages backported to",
    location="args",
)
dp_type = parser.register_item(
    "dp_type",
    type=str,
    choices=("both", "source", "binary"),
    default="both",
    required=False,
    help="type of dependency [source|binary|both]",
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
arches_list = parser.register_item(
    "archs",
    type=arch_name_type,
    action="split",
    required=False,
    help="architectures to show",
    location="args",
)

pkgs_depends_args = parser.build_parser(branch, dp_name, dp_type_opt)
src_pkg_depends_args = parser.build_parser(branch, depends_depth_opt)
backport_helper_args = parser.build_parser(
    branch_from, branch_to, packages_list, dp_type, arches_list
)
