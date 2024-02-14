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
    branch_name_type,
    errata_id_type,
    packager_name_type,
    positive_integer_type,
    task_search_type,
    packager_nick_type,
    sort_type,
    open_vulns_search_type,
    uuid_type,
    cpe_search_type,
)

from .endpoints.tools.constants import DRY_RUN_KEY

task_input_val_opt = parser.register_item(
    "input",
    type=task_search_type,
    action="split",
    required=False,
    help="task search arguments",
    location="args",
)
package_input_val = parser.register_item(
    "input",
    type=open_vulns_search_type,
    required=False,
    help="source package name or vulnerability number",
    location="args",
)
cpe_input_val = parser.register_item(
    "input",
    type=cpe_search_type,
    required=False,
    help="package name, project name or vulnerability number",
    location="args",
)
branch_name_opt = parser.register_item(
    "branch", type=branch_name_type, required=False, help="branch name", location="args"
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
errata_id = parser.register_item(
    "errata_id", type=errata_id_type, required=True, help="errata ID", location="args"
)
is_errata_opt = parser.register_item(
    "is_errata",
    type=inputs.boolean,
    default=False,
    required=False,
    help="is errata",
    location="args",
)
maintainer_nickname_opt = parser.register_item(
    "maintainer_nickname",
    type=packager_nick_type,
    required=False,
    help="maintainer nickname",
    location="args",
)
by_acl_opt = parser.register_item(
    "by_acl",
    type=str,
    choices=(
        "by_packager",
        "by_nick",
        "by_nick_leader",
        "by_nick_or_group",
        "by_nick_leader_and_group",
    ),
    default="by_packager",
    required=False,
    help="search maintainer's packages by ACL",
    location="args",
)
vuln_severity_opt = parser.register_item(
    "severity",
    type=str,
    choices=(
        "CRITICAL",
        "HIGH",
        "MEDIUM",
        "LOW",
    ),
    required=False,
    help="filter by CVE severity",
    location="args",
)
is_images_opt = parser.register_item(
    "is_images",
    type=inputs.boolean,
    default=False,
    required=False,
    help="filtering by package inclusion in the images",
    location="args",
)
pkg_name = parser.register_item(
    "name",
    type=packager_name_type,
    required=True,
    help="source package name",
    location="args",
)
sort_opt = parser.register_item(
    "sort",
    type=sort_type,
    action="split",
    required=False,
    help="sort arguments",
    location="args",
)
transaction_id_opt = parser.register_item(
    "transaction_id",
    type=uuid_type,
    required=False,
    help="transaction id (UUID)",
    location="args",
)
dry_run = parser.register_item(
    DRY_RUN_KEY,
    type=inputs.boolean,
    default=True,
    required=True,
    help="do not commit changes to DB",
    location="args",
)
is_cpe_discarded_opt = parser.register_item(
    "is_discarded",
    type=inputs.boolean,
    default=False,
    required=False,
    help="show discarded CPE records",
    location="args",
)
all_candidates_opt = parser.register_item(
    "all",
    type=inputs.boolean,
    default=False,
    required=False,
    help="show all CPE candidates",
    location="args",
)

task_list_args = parser.build_parser(
    task_input_val_opt, branch_name_opt, is_errata_opt, page_opt, limit_opt
)
errata_manage_args = parser.build_parser(transaction_id_opt)
errata_manage_get_args = parser.build_parser(errata_id)
pkgs_open_vulns_args = parser.build_parser(
    package_input_val,
    branch_name_opt,
    maintainer_nickname_opt,
    by_acl_opt,
    vuln_severity_opt,
    is_images_opt,
    page_opt,
    limit_opt,
    sort_opt,
)
cpe_candidates_args = parser.build_parser(all_candidates_opt)
cpe_manage_args = parser.build_parser(dry_run)
cpe_manage_get_args = parser.build_parser(pkg_name, branch_name_opt)
maintainer_list_args = parser.build_parser(branch_name_opt, page_opt, limit_opt)
cpe_list_args = parser.build_parser(
    cpe_input_val, page_opt, limit_opt, sort_opt, is_cpe_discarded_opt
)
