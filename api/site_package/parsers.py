from flask_restx import reqparse

all_archs_args = reqparse.RequestParser()
all_archs_args.add_argument(
    "branch", type=str, required=True, help="name of packageset", location="args"
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

pkgs_with_cve_fix_args = reqparse.RequestParser()
pkgs_with_cve_fix_args.add_argument(
    "branch", type=str, required=True, help="name of packageset", location="args"
)

pkgs_binary_list_args = reqparse.RequestParser()
pkgs_binary_list_args.add_argument(
    "branch", type=str, required=True, help="name of packageset", location="args"
)
pkgs_binary_list_args.add_argument(
    "name", type=str, required=True, help="binary package name", location="args"
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

src_pkgs_versions_args = reqparse.RequestParser()
src_pkgs_versions_args.add_argument(
    "name", type=str, required=True, help="source package name", location="args"
)
