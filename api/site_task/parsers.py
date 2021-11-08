from api.base import parser


# base arg parser items
name = parser.register_item(
    "name", type=str, required=True, help="package name", location="args"
)
branch = parser.register_item(
    "branch", type=str, required=True, help="name of packageset", location="args"
)
branch_opt = parser.register_item(
    "branch", type=str, required=False, help="name of packageset", location="args"
)
maintainer_nick = parser.register_item(
    "maintainer_nickname",
    type=str,
    required=True,
    help="nickname of maintainer",
    location="args",
)
task_limit = parser.register_item(
    "tasks_limit",
    type=int,
    default=10,
    required=True,
    help="number of last tasks to get",
    location="args",
)
task_owner = parser.register_item(
    "task_owner",
    type=str,
    required=False,
    help="task owner's nickname",
    location="args",
)

# build parsesr
task_by_name_args = parser.build_parser(name)
maintainer_info_args = parser.build_parser(branch, maintainer_nick)
last_pkgs_args = parser.build_parser(branch, task_limit, task_owner)
pkgs_versions_from_tasks_args = parser.build_parser(name, branch_opt)
