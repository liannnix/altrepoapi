from api.base import parser


name = parser.register_item(
    "name", type=str, required=True, help="package name", location="args"
)
branch = parser.register_item(
    "branch", type=str, required=True, help="name of packageset", location="args"
)
branch_opt = parser.register_item(
    "branch", type=str, required=False, help="name of packageset", location="args"
)
arch = parser.register_item(
    "arch", type=str, required=True, help="package arch", location="args"
)
arch_opt = parser.register_item(
    "arch", type=str, required=False, help="binary package arch", location="args"
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
group = parser.register_item(
    "group", type=str, required=False, help="package category", location="args"
)
buildtime = parser.register_item(
    "buildtime",
    type=int,
    default=0,
    required=False,
    help="package buildtime",
    location="args",
)
packager = parser.register_item(
    "packager",
    type=str,
    required=False,
    help="package packager's nickname",
    location="args",
)
pkgs_limit = parser.register_item(
    "packages_limit",
    type=int,
    default=10,
    required=True,
    help="number of last packages to get",
    location="args",
)


pkgset_packages_args = parser.build_parser(branch, package_type, group, buildtime)
pkgset_pkghash_args = parser.build_parser(branch, name)
pkgset_pkg_binary_hash_args = parser.build_parser(branch, name, arch)
pkgs_by_name_args = parser.build_parser(name, branch_opt, arch_opt)
last_pkgs_branch_args = parser.build_parser(branch, pkgs_limit, packager)
