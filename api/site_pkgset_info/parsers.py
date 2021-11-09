from api.base import parser

branch = parser.register_item(
    "branch", type=str, required=True, help="name of packageset", location="args"
)
package_type = parser.register_item(
    "package_type",
    type=str,
    choices=("all", "source", "binary"),
    default="source",
    required=False,
    help="packages type [source|binary|all]",
    location="args",
)

all_archs_args = parser.build_parser(branch)
pkgset_categories_args = parser.build_parser(branch, package_type)
