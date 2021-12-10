# ALTRepo API
# Copyright (C) 2021  BaseALT Ltd

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from flask_restx import inputs

from altrepo_api.api.parser import (
    parser,
    arch_name_type,
    branch_name_type,
    disttag_type,
    checksum_type,
    pkg_name_type,
    pkg_release_type,
    pkg_version_type,
    file_name_wc_type,
    packager_name_type,
    packager_email_type,
)

# register parser items
branch = parser.register_item(
    "branch",
    type=branch_name_type,
    required=True,
    help="name of packageset",
    location="args",
)
branch_opt = parser.register_item(
    "branch",
    type=branch_name_type,
    required=False,
    help="name of packageset",
    location="args",
)
branch_list_opt = parser.register_item(
    "branches",
    type=branch_name_type,
    action="split",
    required=False,
    help="list of package sets to filter result",
    location="args",
)
file = parser.register_item(
    "file", type=file_name_wc_type, required=True, help="file name", location="args"
)
src_package_name = parser.register_item(
    "name",
    type=pkg_name_type,
    required=True,
    help="source package name",
    location="args",
)
version_opt = parser.register_item(
    "version",
    type=pkg_version_type,
    required=False,
    help="package version",
    location="args",
)
release_opt = parser.register_item(
    "release",
    type=pkg_release_type,
    required=False,
    help="package release",
    location="args",
)
arch_opt = parser.register_item(
    "arch",
    type=arch_name_type,
    required=False,
    help="package architecture",
    location="args",
)
arch_list_opt = parser.register_item(
    "archs",
    type=arch_name_type,
    action="split",
    required=False,
    help="list of packages architectures",
    location="args",
)
package_name = parser.register_item(
    "package_name",
    type=pkg_name_type,
    required=True,
    help="source or binary package name",
    location="args",
)
package_name_opt = parser.register_item(
    "name", type=pkg_name_type, required=False, help="package name", location="args"
)
package_list = parser.register_item(
    "packages",
    type=pkg_name_type,
    action="split",
    required=True,
    help="package or list of packages",
    location="args",
)
package_type_opt = parser.register_item(
    "package_type",
    type=str,
    choices=("source", "binary"),
    default="source",
    required=False,
    help="packages type [source|binary]",
    location="args",
)
package_version_opt = parser.register_item(
    "package_version",
    type=pkg_version_type,
    required=False,
    help="source or binary package version",
    location="args",
)
package_release_opt = parser.register_item(
    "package_release",
    type=pkg_release_type,
    required=False,
    help="source or binary package release",
    location="args",
)
bin_package_arch_opt = parser.register_item(
    "bin_package_arch",
    type=arch_name_type,
    required=False,
    help="binary package arch",
    location="args",
)
source_opt = parser.register_item(
    "source",
    type=inputs.boolean,
    default=False,
    required=False,
    help="is source package",
    location="args",
)
packager = parser.register_item(
    "packager",
    type=packager_name_type,
    required=True,
    help="maintainer nickname",
    location="args",
)
packager_opt = parser.register_item(
    "packager",
    type=packager_name_type,
    required=False,
    help="package packager name",
    location="args",
)
packager_email_opt = parser.register_item(
    "packager_email",
    type=packager_email_type,
    required=False,
    help="package packager email",
    location="args",
)
md5 = parser.register_item(
    "md5", type=checksum_type, required=True, help="file MD5 checksum", location="args"
)
sha1_opt = parser.register_item(
    "sha1",
    type=checksum_type,
    required=False,
    help="package SHA1 checksum",
    location="args",
)
disttag_opt = parser.register_item(
    "disttag",
    type=disttag_type,
    required=False,
    help="package disttag",
    location="args",
)
full_opt = parser.register_item(
    "full",
    type=inputs.boolean,
    default=False,
    required=False,
    help="show full package information",
    location="args",
)
leaf_opt = parser.register_item(
    "leaf",
    type=pkg_name_type,
    required=False,
    help="assembly dependency chain package",
    location="args",
)
depth_opt = parser.register_item(
    "depth",
    type=int,
    default=1,
    required=False,
    help="dependency depth",
    location="args",
)
dptype_opt = parser.register_item(
    "dptype",
    type=str,
    choices=("both", "source", "binary"),
    default="both",
    required=False,
    help="dependency type [source|binary|both]",
    location="args",
)
filter_by_package_list_opt = parser.register_item(
    "filter_by_package",
    type=pkg_name_type,
    action="split",
    required=False,
    help="filter result by dependency on binary packages",
    location="args",
)
filter_by_source_opt = parser.register_item(
    "filter_by_source",
    type=pkg_name_type,
    required=False,
    help="filter result by dependency on source package",
    location="args",
)
finite_package_opt = parser.register_item(
    "finite_package",
    type=inputs.boolean,
    default=False,
    required=False,
    help="topological tree leaves packages",
    location="args",
)
oneandhalf_opt = parser.register_item(
    "oneandhalf",
    type=inputs.boolean,
    default=False,
    required=False,
    help="use dependency depth 1.5",
    location="args",
)
use_last_tasks_opt = parser.register_item(
    "use_last_tasks",
    type=inputs.boolean,
    default=False,
    required=False,
    help="use repo state including last done tasks",
    location="args",
)

# build parsers
package_info_args = parser.build_parser(
    package_name_opt,
    version_opt,
    release_opt,
    arch_opt,
    source_opt,
    branch_opt,
    disttag_opt,
    sha1_opt,
    packager_opt,
    packager_email_opt,
    full_opt,
)
pkg_build_dep_args = parser.build_parser(
    package_list,
    branch,
    depth_opt,
    dptype_opt,
    arch_list_opt,
    leaf_opt,
    finite_package_opt,
    filter_by_package_list_opt,
    filter_by_source_opt,
    oneandhalf_opt,
    use_last_tasks_opt,
)
misconflict_pkg_args = parser.build_parser(
    package_list,
    branch,
    arch_list_opt,
)
pkg_find_pkgset_args = parser.build_parser(package_list, branch_list_opt)
pkg_by_file_name_args = parser.build_parser(file, branch, arch_opt)
pkg_by_file_md5_args = parser.build_parser(branch, md5, arch_opt)
unpackaged_dirs_args = parser.build_parser(branch, packager, arch_list_opt)
build_dep_set_args = parser.build_parser(branch, package_list, arch_list_opt)
pkg_repocop_args = parser.build_parser(
    branch,
    package_name,
    package_version_opt,
    package_release_opt,
    bin_package_arch_opt,
    package_type_opt,
)
specfile_args = parser.build_parser(
    branch,
    src_package_name,
)
