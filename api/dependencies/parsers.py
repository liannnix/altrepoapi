# from flask_restx import reqparse
from api.base import parser

branch = parser.register_item(
    "branch", type=str, required=True, help="packageset name", location="args"
)
dp_name = parser.register_item(
    "dp_name", type=str, required=True, help="dependency name", location="args"
)
dp_type_opt = parser.register_item(
    "dp_type",
    type=str,
    choices=("provide", "require"),
    default="provide",
    required=False,
    help="type of dependency [provide|require]",
    location="args",
)

pkgs_depends_args = parser.build_parser(branch, dp_name, dp_type_opt)
