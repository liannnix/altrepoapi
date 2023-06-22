# ALTRepo API
# Copyright (C) 2021-2023  BaseALT Ltd

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

from altrepo_api.api.parser import (
    parser,
    arch_name_type,
    branch_name_type,
    pkg_name_type,
    pkg_groups_type,
    pkg_version_type,
    pkg_release_type,
    packager_nick_type,
    pkg_name_list_type,
)


name = parser.register_item(
    "name", type=pkg_name_type, required=True, help="package name", location="args"
)
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
arch = parser.register_item(
    "arch", type=arch_name_type, required=True, help="package arch", location="args"
)
arch_opt = parser.register_item(
    "arch",
    type=arch_name_type,
    required=False,
    help="binary package arch",
    location="args",
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
    "group",
    type=pkg_groups_type,
    required=False,
    help="package category",
    location="args",
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
    type=packager_nick_type,
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
package_version = parser.register_item(
    "version",
    type=pkg_version_type,
    required=True,
    help="source package version",
    location="args",
)
package_release = parser.register_item(
    "release",
    type=pkg_release_type,
    required=True,
    help="source package release",
    location="args",
)
package_name_list = parser.register_item(
    "name",
    type=pkg_name_list_type,
    action="split",
    required=True,
    help="package or list of package names",
    location="args",
)

pkgset_packages_args = parser.build_parser(branch, package_type, group, buildtime)
pkgset_pkghash_args = parser.build_parser(branch, name)
pkgset_pkg_binary_hash_args = parser.build_parser(branch, name, arch)
pkgs_by_name_args = parser.build_parser(package_name_list, branch_opt, arch_opt)
pkgs_search_by_name_args = parser.build_parser(package_name_list, branch_opt)
last_pkgs_branch_args = parser.build_parser(branch, pkgs_limit, packager)
pkgset_pkghash_by_nvr = parser.build_parser(
    name, branch, package_version, package_release
)
find_src_pkg_args = parser.build_parser(branch, name)
