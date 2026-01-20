# ALTRepo API
# Copyright (C) 2021-2026  BaseALT Ltd

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

from altrepo_api.api.parser import parser, branch_name_type, file_search_type


# register parser items
branch = parser.register_item(
    "branch",
    type=branch_name_type,
    required=True,
    help="name of packageset",
    location="args",
)
files_limit_opt = parser.register_item(
    "limit",
    type=int,
    required=False,
    default=1000,
    help="number of files to get",
    location="args",
)
fast_lookup_files_limit_opt = parser.register_item(
    "limit",
    type=int,
    required=False,
    default=10,
    help="number of files to get",
    location="args",
)
file_name = parser.register_item(
    "file_name",
    type=file_search_type,
    required=True,
    help="file name or directory",
    location="args",
)

# build parsers
file_search_args = parser.build_parser(branch, file_name, files_limit_opt)
fast_lookup_args = parser.build_parser(branch, file_name, fast_lookup_files_limit_opt)
packages_by_file_args = parser.build_parser(branch, file_name)
