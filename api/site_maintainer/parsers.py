from api.base import parser


branch = parser.register_item(
    "branch", type=str, required=True, help="name of packageset", location="args"
)
maintainer_nick = parser.register_item(
    "maintainer_nickname",
    type=str,
    required=True,
    help="nickname of maintainer",
    location="args",
)

all_maintainers_args = parser.build_parser(branch)
maintainer_info_args = parser.build_parser(branch, maintainer_nick)
maintainer_branches_args = parser.build_parser(maintainer_nick)
