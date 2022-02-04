# ALTRepo API
# Copyright (C) 2021-2022  BaseALT Ltd

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

from altrepo_api.api.parser import parser, branch_name_type, arch_name_type

# register parser items
branch = parser.register_item(
    "branch", type=branch_name_type, required=True, help="name of packageset", location="args"
)
packageset_1 = parser.register_item(
    "pkgset1", type=branch_name_type, required=True, help="first packageset name", location="args"
)
packageset_2 = parser.register_item(
    "pkgset2", type=branch_name_type, required=True, help="second packageset name", location="args"
)
package_type_opt = parser.register_item(
    "package_type",
    type=str,
    choices=("all", "source", "binary"),
    default="all",
    required=False,
    help="packages type [source|binary|all]",
    location="args",
)
arch_list_opt = parser.register_item(
    "archs",
    type=arch_name_type,
    action="split",
    required=False,
    help="list of packages architectures",
    location="args",
)

# build parsers
pkgset_compare_args = parser.build_parser(packageset_1, packageset_2)
pkgset_packages_args = parser.build_parser(branch, package_type_opt, arch_list_opt)
