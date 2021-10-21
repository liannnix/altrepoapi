from flask_restx import reqparse

pkgs_depends_args = reqparse.RequestParser()
pkgs_depends_args.add_argument(
    "dp_name", type=str, required=True, help="dependency name", location="args"
)
pkgs_depends_args.add_argument(
    "branch", type=str, required=True, help="packageset name", location="args"
)
pkgs_depends_args.add_argument(
    "dp_type",
    type=str,
    choices=("provide", "require"),
    default="provide",
    required=False,
    help="type of dependency [provide|require]",
    location="args",
)
