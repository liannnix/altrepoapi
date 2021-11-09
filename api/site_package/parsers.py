from api.base import parser


# base arg parser items
branch = parser.register_item(
    "branch",
    type=str,
    required=True,
    help="name of packageset",
    location="args",
)
pkg_name =parser.register_item(
    "name",
    type=str,
    required=True,
    help="package name",
    location="args",
)
bin_pkg_name = parser.register_item(
    "name",
    type=str,
    required=True,
    help="binary package name",
    location="args",
)
src_pkg_name = parser.register_item(
    "name",
    type=str,
    required=True,
    help="source package name",
    location="args",
)
pkg_type = parser.register_item(
    "package_type",
    type=str,
    choices=("source", "binary"),
    default="source",
    required=False,
    help="packages type [source|binary]",
    location="args",
)
changelog = parser.register_item(
    "changelog_last",
    type=int,
    default=3,
    required=False,
    help="changelog history length",
    location="args",
)
arch = parser.register_item(
    "arch",
    type=str,
    required=True,
    help="arch of binary packages",
    location="args",
)
arch_opt = parser.register_item(
    "arch",
    type=str,
    required=False,
    help="arch of binary packages",
    location="args",
)

# build parsesr
src_downloads_args = parser.build_parser(branch)
bin_downloads_args = parser.build_parser(branch, arch)
package_chlog_args = parser.build_parser(changelog)
pkgs_with_cve_fix_args = parser.build_parser(branch)
src_pkgs_versions_args = parser.build_parser(src_pkg_name)
pkgs_versions_args = parser.build_parser(src_pkg_name, pkg_type, arch_opt)
pkgs_binary_list_args = parser.build_parser(branch, bin_pkg_name)
package_info_args = parser.build_parser(branch, changelog, pkg_type)
deleted_package_args = parser.build_parser(branch, pkg_name, pkg_type, arch_opt)
