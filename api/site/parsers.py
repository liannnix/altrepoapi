from flask_restx import reqparse


package_info_args = reqparse.RequestParser()
package_info_args.add_argument(
    "branch", type=str, required=True, help="name of packageset", location="args"
)
package_info_args.add_argument(
    "changelog_last",
    type=int,
    default=3,
    required=False,
    help="changelog history length",
    location="args",
)
package_info_args.add_argument(
    "package_type",
    type=str,
    choices=("source", "binary"),
    default="source",
    required=False,
    help="packages type [source|binary]",
    location="args",
)

pkgset_packages_args = reqparse.RequestParser()
pkgset_packages_args.add_argument(
    "branch", type=str, required=True, help="name of packageset", location="args"
)
pkgset_packages_args.add_argument(
    "package_type",
    type=str,
    choices=("all", "source", "binary"),
    default="source",
    required=False,
    help="packages type [source|binary|all]",
    location="args",
)
pkgset_packages_args.add_argument(
    "group", type=str, required=False, help="package category", location="args"
)
pkgset_packages_args.add_argument(
    "buildtime",
    type=int,
    default=0,
    required=False,
    help="package buildtime",
    location="args",
)

package_chlog_args = reqparse.RequestParser()
package_chlog_args.add_argument(
    "changelog_last",
    type=int,
    default=1,
    required=False,
    help="changelog history length",
    location="args",
)

pkgset_pkghash_args = reqparse.RequestParser()
pkgset_pkghash_args.add_argument(
    "branch", type=str, required=True, help="name of packageset", location="args"
)
pkgset_pkghash_args.add_argument(
    "name", type=str, required=True, help="package name", location="args"
)

pkgset_pkg_binary_hash_args = reqparse.RequestParser()
pkgset_pkg_binary_hash_args.add_argument(
    "branch", type=str, required=True, help="name of packageset", location="args"
)
pkgset_pkg_binary_hash_args.add_argument(
    "name", type=str, required=True, help="package name", location="args"
)
pkgset_pkg_binary_hash_args.add_argument(
    "arch", type=str, required=True, help="package arch", location="args"
)

task_by_name_args = reqparse.RequestParser()
task_by_name_args.add_argument(
    "name", type=str, required=True, help="package name", location="args"
)

pkgs_by_name_args = reqparse.RequestParser()
pkgs_by_name_args.add_argument(
    "name", type=str, required=True, help="package name", location="args"
)
pkgs_by_name_args.add_argument(
    "branch", type=str, required=False, help="name of packageset", location="args"
)
pkgs_by_name_args.add_argument(
    "arch", type=str, required=False, help="arch of binary packages", location="args"
)

last_pkgs_args = reqparse.RequestParser()
last_pkgs_args.add_argument(
    "branch", type=str, required=True, help="name of packageset", location="args"
)
last_pkgs_args.add_argument(
    "tasks_limit",
    type=int,
    default=10,
    required=True,
    help="number of last tasks to get",
    location="args",
)
last_pkgs_args.add_argument(
    "task_owner", type=str, required=False, help="task owner's nickname", location="args"
)

pkgset_categories_args = reqparse.RequestParser()
pkgset_categories_args.add_argument(
    "branch", type=str, required=True, help="name of packageset", location="args"
)
pkgset_categories_args.add_argument(
    "package_type",
    type=str,
    choices=("all", "source", "binary"),
    default="source",
    required=False,
    help="packages type [source|binary|all]",
    location="args",
)

all_archs_args = reqparse.RequestParser()
all_archs_args.add_argument(
    "branch", type=str, required=True, help="name of packageset", location="args"
)

all_maintainers_args = reqparse.RequestParser()
all_maintainers_args.add_argument(
    "branch", type=str, required=True, help="name of packageset", location="args"
)
maintainer_info_args = reqparse.RequestParser()
maintainer_info_args.add_argument(
    "maintainer_nickname",
    type=str,
    required=True,
    help="nickname of maintainer",
    location="args",
)
maintainer_info_args.add_argument(
    "branch", type=str, required=True, help="name of packageset", location="args"
)

maintainer_branches_args = reqparse.RequestParser()
maintainer_branches_args.add_argument(
    "maintainer_nickname",
    type=str,
    required=True,
    help="nickname of maintainer",
    location="args",
)

pkgs_with_cve_fix_args = reqparse.RequestParser()
pkgs_with_cve_fix_args.add_argument(
    "branch", type=str, required=True, help="name of packageset", location="args"
)

deleted_package_args = reqparse.RequestParser()
deleted_package_args.add_argument(
    "branch", type=str, required=True, help="name of packageset", location="args"
)
deleted_package_args.add_argument(
    "name", type=str, required=True, help="package name", location="args"
)
deleted_package_args.add_argument(
    "package_type",
    type=str,
    choices=("source", "binary"),
    default="source",
    required=False,
    help="packages type [source|binary]",
    location="args",
)
deleted_package_args.add_argument(
    "arch", type=str, required=False, help="arch of binary packages", location="args"
)

last_pkgs_branch_args = reqparse.RequestParser()
last_pkgs_branch_args.add_argument(
    "branch", type=str, required=True, help="name of packageset", location="args"
)
last_pkgs_branch_args.add_argument(
    "packages_limit",
    type=int,
    default=10,
    required=True,
    help="number of last packages to get",
    location="args",
)
last_pkgs_branch_args.add_argument(
    "packager", type=str, required=False, help="package packager's nickname", location="args"
)

pkgs_versions_from_tasks_args = reqparse.RequestParser()
pkgs_versions_from_tasks_args.add_argument(
    "name", type=str, required=True, help="source package name", location="args"
)
pkgs_versions_from_tasks_args.add_argument(
    "branch", type=str, required=False, help="packageset name", location="args"
)

pkgs_binary_list_args = reqparse.RequestParser()
pkgs_binary_list_args.add_argument(
    "branch", type=str, required=True, help="name of packageset", location="args"
)
pkgs_binary_list_args.add_argument(
    "name", type=str, required=True, help="binary package name", location="args"
)

src_pkgs_versions_args = reqparse.RequestParser()
src_pkgs_versions_args.add_argument(
    "name", type=str, required=True, help="source package name", location="args"
)
