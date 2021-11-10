from flask_restx import inputs
from api.base import parser

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
    type=str,
    action="split",
    required=False,
    help="list of packages architectures",
    location="args",
)
branch_list_opt = parser.register_item(
    "branches",
    type=str,
    action="split",
    required=False,
    help="list of package sets to filter result",
    location="args",
)
leaf_opt = parser.register_item(
    "leaf",
    type=str,
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
    type=str,
    action="split",
    required=False,
    help="filter result by dependency on binary packages",
    location="args",
)
filter_by_source_opt = parser.register_item(
    "filter_by_source",
    type=str,
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
