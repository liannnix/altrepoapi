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

from altrepo_api.api.parser import parser, arch_name_type, branch_name_type

# register parser items
arch_opt = parser.register_item(
    "arch",
    type=arch_name_type,
    required=False,
    help="package architecture",
    location="args",
)
branch_list = parser.register_item(
    "branches",
    type=branch_name_type,
    action="split",
    required=True,
    help="list of package sets to filter result",
    location="args",
)

# build parsers
pkgset_packages_args = parser.build_parser(arch_opt)
translation_export_args = parser.build_parser(branch_list)
