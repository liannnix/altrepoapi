# ALTRepo API
# Copyright (C) 2024 BaseALT Ltd

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

from altrepo_api.api.parser import parser, positive_integer_type, sort_type

sort_opt = parser.register_item(
    "sort",
    type=sort_type,
    action="split",
    required=False,
    help="sort arguments",
    location="args",
)
branch_name_opt = parser.register_item(
    "branch", type=str, required=False, help="branch name", location="args"
)
limit_opt = parser.register_item(
    "limit",
    type=positive_integer_type,
    required=False,
    help="number of records",
    location="args",
)
page_opt = parser.register_item(
    "page",
    type=positive_integer_type,
    required=False,
    help="number page",
    location="args",
)
av_pkg_name_input_val = parser.register_item(
    "input",
    type=str,
    required=False,
    help="package name or message",
    location="args",
)
av_scanner_opt = parser.register_item(
    "scanner",
    type=str,
    required=False,
    help="scanner name",
    location="args",
)
av_issue_opt = parser.register_item(
    "issue",
    type=str,
    required=False,
    help="antivirus detection issue",
    location="args",
)
avs_pkg_list_args = parser.build_parser(
    av_pkg_name_input_val,
    page_opt,
    limit_opt,
    sort_opt,
    branch_name_opt,
    av_scanner_opt,
    av_issue_opt,
)
