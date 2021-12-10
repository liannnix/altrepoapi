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

from flask_restx import inputs

from altrepo_api.api.parser import (
    parser,
    arch_name_type,
    branch_name_type,
    pkg_name_type,
    date_string_type,
)

# register parser items
try_opt = parser.register_item(
    "try", type=int, required=False, help="task try", location="args"
)
iteration_opt = parser.register_item(
    "iteration", type=int, required=False, help="task iteration", location="args"
)
include_task_packages_opt = parser.register_item(
    "include_task_packages",
    type=inputs.boolean,
    required=False,
    default=False,
    help="include task packages in repository state",
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
branch_list_opt = parser.register_item(
    "branches",
    type=branch_name_type,
    action="split",
    required=False,
    help="list of package sets to filter result",
    location="args",
)
leaf_opt = parser.register_item(
    "leaf",
    type=pkg_name_type,
    required=False,
    help="assembly dependency chain package",
    location="args",
)
depth_opt = parser.register_item(
    "depth",
    type=int,
    default=1,
    required=False,
    help="dependency depth",
    location="args",
)
dptype_opt = parser.register_item(
    "dptype",
    type=str,
    choices=("both", "source", "binary"),
    default="both",
    required=False,
    help="dependency type [source|binary|both]",
    location="args",
)
filter_by_package_list_opt = parser.register_item(
    "filter_by_package",
    type=pkg_name_type,
    action="split",
    required=False,
    help="filter result by dependency on binary packages",
    location="args",
)
filter_by_source_opt = parser.register_item(
    "filter_by_source",
    type=pkg_name_type,
    required=False,
    help="filter result by dependency on source package",
    location="args",
)
finite_package_opt = parser.register_item(
    "finite_package",
    type=inputs.boolean,
    default=False,
    required=False,
    help="topological tree leaves packages",
    location="args",
)
oneandhalf_opt = parser.register_item(
    "oneandhalf",
    type=inputs.boolean,
    default=False,
    required=False,
    help="use dependency depth 1.5",
    location="args",
)
branch = parser.register_item(
    "branch",
    type=branch_name_type,
    required=True,
    help="name of packageset",
    location="args",
)
start_task_opt = parser.register_item(
    "start_task",
    type=int,
    default=0,
    required=False,
    help="start task ID",
    location="args",
)
end_task_opt = parser.register_item(
    "end_task",
    type=int,
    default=0,
    required=False,
    help="end task ID",
    location="args",
)
start_date_opt = parser.register_item(
    "start_date",
    type=date_string_type,
    default=None,
    required=False,
    help="task history start date (YYYY-MM-DD)",
    location="args",
)
end_date_opt = parser.register_item(
    "end_date",
    type=date_string_type,
    default=None,
    required=False,
    help="task history end date (YYYY-MM-DD)",
    location="args",
)

# build parsers
task_info_args = parser.build_parser(try_opt, iteration_opt)
task_repo_args = parser.build_parser(include_task_packages_opt)
task_build_dep_args = parser.build_parser(
    depth_opt,
    dptype_opt,
    arch_list_opt,
    leaf_opt,
    finite_package_opt,
    filter_by_package_list_opt,
    filter_by_source_opt,
    oneandhalf_opt,
)
task_misconflict_args = parser.build_parser(arch_list_opt)
task_find_pkgset_args = parser.build_parser(branch_list_opt)
task_buid_dep_set_args = parser.build_parser(arch_list_opt)
task_history_args = parser.build_parser(
    branch, start_task_opt, end_task_opt, start_date_opt, end_date_opt
)
