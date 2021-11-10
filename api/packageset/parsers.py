from api.base import parser

# register parser items
branch = parser.register_item(
    "branch", type=str, required=True, help="name of packageset", location="args"
)
packageset_1 = parser.register_item(
    "pkgset1", type=str, required=True, help="first packageset name", location="args"
)
packageset_2 = parser.register_item(
    "pkgset2", type=str, required=True, help="second packageset name", location="args"
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
    type=str,
    action="split",
    required=False,
    help="list of packages architectures",
    location="args",
)

# build parsers
pkgset_compare_args = parser.build_parser(packageset_1, packageset_2)
pkgset_packages_args = parser.build_parser(branch, package_type_opt, arch_list_opt)
