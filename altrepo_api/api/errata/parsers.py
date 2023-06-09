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

from flask_restx import inputs

from altrepo_api.api.parser import parser, pkg_name_type, errataid_type, branch_name_type

package_name_opt = parser.register_item(
    "package_name",
    type=pkg_name_type,
    required=False,
    help="source or binary package name",
    location="args",
)
one_file_opt = parser.register_item(
    "one_file",
    type=inputs.boolean,
    default=False,
    required=False,
    help="return OVAL definitions as one XML file",
    location="args",
)
errataid_opt = parser.register_item(
    "errata_id",
    required=False,
    help="errata ID",
    location="args",
)
branch_name_opt = parser.register_item(
    "branch",
    type=branch_name_type,
    required=False,
    help="branch name",
    location="args"
)

oval_export_args = parser.build_parser(package_name_opt, one_file_opt)
errata_search_args = parser.build_parser(branch_name_opt, package_name_opt, errataid_opt)
