from flask_restx import reqparse, inputs

package_info_args = reqparse.RequestParser()
package_info_args.add_argument(
    "sha1", type=str, required=False, help="package SHA1 checksum", location="args"
)
package_info_args.add_argument(
    "name", type=str, required=False, help="package name", location="args"
)
package_info_args.add_argument(
    "version", type=str, required=False, help="package version", location="args"
)
package_info_args.add_argument(
    "release", type=str, required=False, help="package release", location="args"
)
package_info_args.add_argument(
    "arch", type=str, required=False, help="package arch", location="args"
)
package_info_args.add_argument(
    "disttag", type=str, required=False, help="package disttag", location="args"
)
package_info_args.add_argument(
    "source",
    type=inputs.boolean,
    default=False,
    required=False,
    help="is source package",
    location="args",
)
package_info_args.add_argument(
    "packager", type=str, required=False, help="package packager name", location="args"
)
package_info_args.add_argument(
    "packager_email",
    type=str,
    required=False,
    help="package packager email",
    location="args",
)
package_info_args.add_argument(
    "branch", type=str, required=False, help="name of packageset", location="args"
)
package_info_args.add_argument(
    "full",
    type=inputs.boolean,
    default=False,
    required=False,
    help="show full package information",
    location="args",
)


pkg_build_dep_args = reqparse.RequestParser()
pkg_build_dep_args.add_argument(
    "packages",
    type=str,
    action="split",
    required=True,
    help="package or list of packages",
    location="args",
)
pkg_build_dep_args.add_argument(
    "branch", type=str, required=True, help="name of packageset", location="args"
)
pkg_build_dep_args.add_argument(
    "arch",
    type=str,
    action="split",
    required=False,
    help="list of packages architectures",
    location="args",
)
pkg_build_dep_args.add_argument(
    "leaf",
    type=str,
    required=False,
    help="assembly dependency chain package",
    location="args",
)
pkg_build_dep_args.add_argument(
    "depth",
    type=int,
    default=1,
    required=False,
    help="dependency depth",
    location="args",
)
pkg_build_dep_args.add_argument(
    "dptype",
    type=str,
    choices=("both", "source", "binary"),
    default="both",
    required=False,
    help="dependency type [source|binary|both]",
    location="args",
)
pkg_build_dep_args.add_argument(
    "filter_by_package",
    type=str,
    action="split",
    required=False,
    help="filter result by dependency on binary packages",
    location="args",
)
pkg_build_dep_args.add_argument(
    "filter_by_source",
    type=str,
    # action='split',
    required=False,
    help="filter result by dependency on source package",
    location="args",
)
pkg_build_dep_args.add_argument(
    "finite_package",
    type=inputs.boolean,
    default=False,
    required=False,
    help="topological tree leaves packages",
    location="args",
)
pkg_build_dep_args.add_argument(
    "oneandhalf",
    type=inputs.boolean,
    default=False,
    required=False,
    help="use dependency depth 1.5",
    location="args",
)

misconflict_pkg_args = reqparse.RequestParser()
misconflict_pkg_args.add_argument(
    "packages",
    type=str,
    action="split",
    required=True,
    help="package or list of packages",
    location="args",
)
misconflict_pkg_args.add_argument(
    "branch", type=str, required=True, help="name of packageset", location="args"
)
misconflict_pkg_args.add_argument(
    "archs",
    type=str,
    action="split",
    required=False,
    help="list of packages architectures",
    location="args",
)

pkg_find_pkgset_args = reqparse.RequestParser()
pkg_find_pkgset_args.add_argument(
    "packages",
    type=str,
    action="split",
    required=True,
    help="package or list of packages",
    location="args",
)
pkg_find_pkgset_args.add_argument(
    "branches",
    type=str,
    action="split",
    required=False,
    help="list of package sets to filter result",
    location="args",
)

pkg_by_file_name_args = reqparse.RequestParser()
pkg_by_file_name_args.add_argument(
    "file", type=str, required=True, help="file name", location="args"
)
pkg_by_file_name_args.add_argument(
    "branch", type=str, required=True, help="name of package set", location="args"
)
pkg_by_file_name_args.add_argument(
    "arch", type=str, required=False, help="packages architecture", location="args"
)

pkg_by_file_md5_args = reqparse.RequestParser()
pkg_by_file_md5_args.add_argument(
    "md5", type=str, required=True, help="file MD5 checksum", location="args"
)
pkg_by_file_md5_args.add_argument(
    "branch", type=str, required=True, help="name of package set", location="args"
)
pkg_by_file_md5_args.add_argument(
    "arch", type=str, required=False, help="packages architecture", location="args"
)

dependent_packages_args = reqparse.RequestParser()
dependent_packages_args.add_argument(
    "name", type=str, required=True, help="package name", location="args"
)
dependent_packages_args.add_argument(
    "branch", type=str, required=True, help="name of package set", location="args"
)

unpackaged_dirs_args = reqparse.RequestParser()
unpackaged_dirs_args.add_argument(
    "packager", type=str, required=True, help="maintainer nickname", location="args"
)
unpackaged_dirs_args.add_argument(
    "branch", type=str, required=True, help="name of package set", location="args"
)
unpackaged_dirs_args.add_argument(
    "archs",
    type=str,
    action="split",
    required=False,
    help="list of packages architectures",
    location="args",
)

build_dep_set_args = reqparse.RequestParser()
build_dep_set_args.add_argument(
    "packages",
    type=str,
    action="split",
    required=True,
    help="package or list of packages",
    location="args",
)
build_dep_set_args.add_argument(
    "branch", type=str, required=True, help="name of packageset", location="args"
)
build_dep_set_args.add_argument(
    "archs",
    type=str,
    action="split",
    required=False,
    help="list of packages architectures",
    location="args",
)

pkg_repocop_args = reqparse.RequestParser()
pkg_repocop_args.add_argument(
    "branch", type=str, required=True, help="package branch", location="args"
)
pkg_repocop_args.add_argument(
    "srcpkg_name", type=str, required=True, help="source package name", location="args"
)
pkg_repocop_args.add_argument(
    "srcpkg_version",
    type=str,
    required=False,
    help="source package version",
    location="args",
)
pkg_repocop_args.add_argument(
    "srcpkg_release",
    type=str,
    required=False,
    help="source package release",
    location="args",
)
