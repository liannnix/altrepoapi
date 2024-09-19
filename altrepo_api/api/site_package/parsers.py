# ALTRepo API
# Copyright (C) 2021-2024  BaseALT Ltd

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
    pkg_name_type,
    branch_name_type,
    arch_name_type,
)


# base arg parser items
branch = parser.register_item(
    "branch",
    type=branch_name_type,
    required=True,
    help="name of packageset",
    location="args",
)
pkg_name = parser.register_item(
    "name",
    type=pkg_name_type,
    required=True,
    help="package name",
    location="args",
)
bin_pkg_name = parser.register_item(
    "name",
    type=pkg_name_type,
    required=True,
    help="binary package name",
    location="args",
)
src_pkg_name = parser.register_item(
    "name",
    type=pkg_name_type,
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
    type=arch_name_type,
    required=True,
    help="arch of binary packages",
    location="args",
)
arch_opt = parser.register_item(
    "arch",
    type=arch_name_type,
    required=False,
    help="arch of binary packages",
    location="args",
)
pkg_name_opt = parser.register_item(
    "name",
    type=pkg_name_type,
    required=False,
    help="package name",
    location="args",
)

# build parsers
src_downloads_args = parser.build_parser(branch)
bin_downloads_args = parser.build_parser(branch, arch)
package_chlog_args = parser.build_parser(changelog)
pkgs_with_cve_fix_args = parser.build_parser(branch)
src_pkgs_versions_args = parser.build_parser(src_pkg_name)
pkgs_versions_args = parser.build_parser(src_pkg_name, pkg_type, arch_opt)
pkgs_binary_list_args = parser.build_parser(branch, bin_pkg_name)
package_info_args = parser.build_parser(branch, changelog, pkg_type)
deleted_package_args = parser.build_parser(branch, pkg_name, pkg_type, arch_opt)
pkg_nvr_by_hash_args = parser.build_parser(pkg_name_opt)
pkg_misconflict_args = parser.build_parser(branch)
pkg_name_conv_args = parser.build_parser(branch, src_pkg_name)
