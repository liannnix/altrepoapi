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

from altrepo_api.api.parser import (
    parser,
    errata_id_type,
    pkg_name_type,
    branch_name_type,
    errata_search_type,
    positive_integer_type,
)

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
errata_id_opt = parser.register_item(
    "errata_id",
    type=errata_id_type,
    required=False,
    help="errata ID",
    location="args",
)
branch_name_opt = parser.register_item(
    "branch", type=branch_name_type, required=False, help="branch name", location="args"
)
errata_pkg_name_opt = parser.register_item(
    "name",
    type=pkg_name_type,
    required=False,
    help="source package name",
    location="args",
)
vuln_id_opt = parser.register_item(
    "vuln_id", type=str, required=False, help="CVE, BDU or Bug ID", location="args"
)
errata_type_opt = parser.register_item(
    "type",
    type=str,
    choices=("packages", "repository"),
    required=False,
    help="errata type [packages|repository]",
    location="args",
)
last_chngs_limit_opt = parser.register_item(
    "limit",
    type=int,
    required=False,
    default=1000,
    help="number of last errata to get",
    location="args",
)
input_val_opt = parser.register_item(
    "input",
    type=errata_search_type,
    action="split",
    required=False,
    help="errata search arguments",
    location="args",
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
is_discarded = parser.register_item(
    "is_discarded",
    type=inputs.boolean,
    default=False,
    required=False,
    help="is errata discarded",
    location="args",
)

oval_export_args = parser.build_parser(package_name_opt, one_file_opt)
errata_search_args = parser.build_parser(
    branch_name_opt, errata_pkg_name_opt, vuln_id_opt, errata_id_opt
)
find_erratas_args = parser.build_parser(
    input_val_opt, branch_name_opt, errata_type_opt, page_opt, limit_opt, is_discarded
)
