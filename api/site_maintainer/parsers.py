from flask_restx import inputs

from api.base import parser


by_acl_opt = parser.register_item(
    "by_acl",
    type=inputs.boolean,
    required=False,
    default=False,
    help="search maintainer's packages by ACL",
    location="args",
)
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
maintainer_packages_args = parser.build_parser(branch, maintainer_nick, by_acl_opt)
maintainer_branches_args = parser.build_parser(maintainer_nick)
