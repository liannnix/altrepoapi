# ALTRepo API
# Copyright (C) 2021-2025  BaseALT Ltd

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

from flask_restx import inputs

from altrepo_api.api.parser import (
    parser,
    branch_name_type,
    arch_name_type,
    uuid_type,
    arch_component_name_type,
    repo_component_type,
)

# register parser items
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
    help="name of packageset",
    location="args",
)
packageset_1 = parser.register_item(
    "pkgset1",
    type=branch_name_type,
    required=True,
    help="first packageset name",
    location="args",
)
packageset_2 = parser.register_item(
    "pkgset2",
    type=branch_name_type,
    required=True,
    help="second packageset name",
    location="args",
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
include_done_tasks = parser.register_item(
    "include_done_tasks",
    type=inputs.boolean,
    required=False,
    default=False,
    help="include packages from tasks in DONE state",
    location="args",
)
uuid = parser.register_item(
    "uuid",
    type=uuid_type,
    required=True,
    help="packageset component UUID",
    location="args",
)
arch = parser.register_item(
    "arch",
    type=arch_component_name_type,
    required=True,
    help="architecture name",
    location="args",
)
component = parser.register_item(
    "component",
    type=repo_component_type,
    required=True,
    help="component name",
    location="args",
)

# build parsers
pkgset_compare_args = parser.build_parser(packageset_1, packageset_2)
pkgset_packages_args = parser.build_parser(
    branch, package_type_opt, arch_list_opt, include_done_tasks
)
repository_statistics_args = parser.build_parser(branch_opt)
packages_by_uuid_args = parser.build_parser(uuid)
packages_by_component_args = parser.build_parser(branch, arch, component)
