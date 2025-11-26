# ALTRepo API
# Copyright (C) 2021-2025  BaseALT Ltd

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
    cpe_search_type,
    errata_id_type,
    open_vulns_search_type,
    pkg_name_type,
    packager_nick_type,
    positive_integer_type,
    project_name_type,
    sort_type,
    task_search_type,
    uuid_type,
    pkg_name_list_type,
    image_file_type,
    date_string_type,
)

from .endpoints.tools.constants import DEFAULT_REASON_ACTION_TYPES, DRY_RUN_KEY

from ..misc import lut

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
image_opt = parser.register_item(
    "img",
    type=image_file_type,
    required=False,
    help="image file name",
    location="args",
)
package_name = parser.register_item(
    "package_name",
    type=pkg_name_type,
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
package_name_opt = parser.register_item(
    "package_name",
    type=pkg_name_type,
    required=False,
    help="package name",
    location="args",
)
project_name_opt = parser.register_item(
    "project_name",
    type=project_name_type,
    required=False,
    help="common project name",
    location="args",
)
pnc_state_opt = parser.register_item(
    "state",
    choices=(
        "all",
        "active",
        "inactive",
    ),
    default="all",
    required=False,
    help="PNC record state",
    location="args",
)
task_state_opt = parser.register_item(
    "state",
    choices=(
        "all",
        "DONE",
        "EPERM",
        "TESTED",
    ),
    default="all",
    required=False,
    help="task state",
    location="args",
)
pnc_input_opt = parser.register_item(
    "input",
    type=pkg_name_type,
    required=False,
    help="package name or common project name",
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
vuln_input_val = parser.register_item(
    "input",
    type=cpe_search_type,
    required=False,
    help="vulnerability number or errata ID",
    location="args",
)
vuln_our_opt = parser.register_item(
    "our",
    type=inputs.boolean,
    required=False,
    help="",
    location="args",
)
errata_state_opt = parser.register_item(
    "state",
    choices=(
        "all",
        "active",
        "inactive",
    ),
    default="all",
    required=False,
    help="Errata record state",
    location="args",
)
sa_type_opt = parser.register_item(
    "type",
    choices=("all", "cve", "cpe", "package", "advisory"),
    default="all",
    required=False,
    help="Errata SA record type",
    location="args",
)
sa_filter_entry_opt = parser.register_item(
    "filter",
    type=str,
    required=False,
    help="Errata SA type filter contents: CVE ID, CPE string or package name",
    location="args",
)
manage_user = parser.register_item(
    "user",
    type=str,
    required=True,
    help="Management request user name",
    location="args",
)
vuln_modified_start_date_opt = parser.register_item(
    "modified_start_date",
    type=date_string_type,
    required=False,
    help="Start of the date range for modified date.",
    location="args",
)
vuln_modified_end_date_opt = parser.register_item(
    "modified_end_date",
    type=date_string_type,
    required=False,
    help="End of the date range for modified date.",
    location="args",
)
vuln_published_start_date_opt = parser.register_item(
    "published_start_date",
    type=date_string_type,
    required=False,
    help="Start of the date range for published date.",
    location="args",
)
vuln_published_end_date_opt = parser.register_item(
    "published_end_date",
    type=date_string_type,
    required=False,
    help="End of the date range for published date.",
    location="args",
)
manage_user_opt = parser.register_item(
    "user",
    type=str,
    required=False,
    help="Management request user name",
    location="args",
)
event_start_date_opt = parser.register_item(
    "event_start_date",
    type=date_string_type,
    required=False,
    help="Start of the date range for event date.",
    location="args",
)
event_end_date_opt = parser.register_item(
    "event_end_date",
    type=date_string_type,
    required=False,
    help="End of the date range for event date.",
    location="args",
)
chngs_module_opt = parser.register_item(
    "module",
    choices=(
        "all",
        "errata",
        "pnc",
    ),
    default="all",
    required=False,
    help="change module",
    location="args",
)
chngs_change_type_opt = parser.register_item(
    "change_type",
    choices=(
        "all",
        "create",
        "discard",
        "update",
    ),
    default="all",
    required=False,
    help="change type",
    location="args",
)
input_val_opt = parser.register_item(
    "input",
    type=cpe_search_type,
    action="split",
    required=False,
    help=(
        "Search across multiple fields. Looks for matches in: "
        "Errata ID, package name, CPE identifier, task ID package name, "
        "PNC project name."
    ),
    location="args",
)
entity_type = parser.register_item(
    "entity_type",
    type=str,
    required=True,
    help="Entity type",
    location="args",
)
entity_link = parser.register_item(
    "entity_link",
    type=str,
    required=True,
    help="Entity link",
    location="args",
)
default_reason_text_opt = parser.register_item(
    "text",
    type=str,
    required=False,
    help="Search among default reasons` text.",
    location="args",
)
default_reason_source_opt = parser.register_item(
    "source",
    type=str,
    choices=lut.default_reason_source_types,
    help="For what source is default reason",
    location="args",
)
default_reason_is_active_opt = parser.register_item(
    "is_active", type=inputs.boolean, help="Is default reason active", location="args"
)
default_reason_action_list_opt = parser.register_item(
    "action",
    type=str,
    required=False,
    action="split",
    help=f"Default reason`s actions list: {DEFAULT_REASON_ACTION_TYPES}",
    location="args",
)
vuln_status_input_val_opt = parser.register_item(
    "input",
    type=cpe_search_type,
    action="split",
    required=False,
    help=(
        "Search across multiple fields. Looks for matches in: "
        "vulnerability ID, author, status, resolution and subscribers"
    ),
    location="args",
)
vuln_status_status_opt = parser.register_item(
    "status",
    type=str,
    required=False,
    choices=lut.vuln_status_statuses,
    help="Vulnerability status' statuses list: " + ", ".join(lut.vuln_status_statuses),
    location="args",
)
vuln_status_resolution_opt = parser.register_item(
    "resolution",
    type=str,
    required=False,
    choices=lut.vuln_status_resolutions,
    help="Vulnerability status' resolutions list: "
    + ", ".join(lut.vuln_status_resolutions),
    location="args",
)
user_name_input = parser.register_item(
    "input",
    type=packager_nick_type,
    required=True,
    help="User name input",
    location="args",
)
vuln_type_opt = parser.register_item(
    "type",
    type=str,
    required=False,
    choices=("all", *lut.vuln_types),
    help="Vulnerability type: " + ", ".join(lut.vuln_types),
    location="args",
)

user_name = parser.register_item(
    "name",
    type=packager_nick_type,
    required=True,
    help="User name",
    location="args",
)
user_name_opt = parser.register_item(
    "name",
    type=packager_nick_type,
    required=False,
    help="User name",
    location="args",
)
user_aliases_opt = parser.register_item(
    "aliases",
    type=str,
    required=False,
    action="split",
    help="User aliases",
    location="args",
    default=[],
)
manual_errata_changes_opt = parser.register_item(
    "manual_errata_changes",
    type=inputs.boolean,
    required=False,
    default=True,
    help="Filter errata changes for manual only",
    location="args",
)
tracking_input_opt = parser.register_item(
    "input",
    type=cpe_search_type,
    action="split",
    required=False,
    help=(
        "Search across multiple fields. Looks for matches in: "
        "vulnerability ID, errata ID and package name"
    ),
    location="args",
)
tracking_type_opt = parser.register_item(
    "type",
    type=str,
    required=False,
    choices=lut.errata_user_subscription_types,
    help="Tracking entity type (one of: {types})".format(
        types=", ".join(lut.errata_user_subscription_types)
    ),
    location="args",
)
tracking_action_opt = parser.register_item(
    "action",
    type=str,
    required=False,
    choices=("create", "update", "discard"),
    help="Tracking entity action (one of: create, update, discard)",
    location="args",
)
subscribed_start_date = parser.register_item(
    "subscribed_start_date",
    type=date_string_type,
    required=False,
    help="Start date of subscription",
    location="args",
)
subscribed_end_date = parser.register_item(
    "subscribed_end_date",
    type=date_string_type,
    required=False,
    help="End date of subscription.",
    location="args",
)

task_list_args = parser.build_parser(
    task_input_val_opt,
    branch_name_opt,
    task_state_opt,
    is_errata_opt,
    page_opt,
    limit_opt,
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
    image_opt,
    page_opt,
    limit_opt,
    sort_opt,
)
pkgs_unmapped_args = parser.build_parser(package_name_list)
cpe_candidates_args = parser.build_parser(all_candidates_opt, page_opt, limit_opt)
cpe_manage_args = parser.build_parser(dry_run, package_name_opt)
cpe_manage_get_args = parser.build_parser(package_name, branch_name_opt)
maintainer_list_args = parser.build_parser(branch_name_opt, page_opt, limit_opt)
cpe_list_args = parser.build_parser(
    cpe_input_val, page_opt, limit_opt, sort_opt, is_cpe_discarded_opt
)
pnc_manage_args = parser.build_parser(dry_run)
pnc_manage_get_args = parser.build_parser(
    package_name_opt, project_name_opt, pnc_state_opt
)
pnc_list_args = parser.build_parser(
    pnc_input_opt, pnc_state_opt, branch_name_opt, page_opt, limit_opt
)
vuln_list_args = parser.build_parser(
    vuln_input_val,
    vuln_severity_opt,
    vuln_status_status_opt,
    vuln_status_resolution_opt,
    is_errata_opt,
    vuln_our_opt,
    page_opt,
    limit_opt,
    sort_opt,
    vuln_modified_start_date_opt,
    vuln_modified_end_date_opt,
    vuln_published_start_date_opt,
    vuln_published_end_date_opt,
    vuln_type_opt,
)
sa_list_args = parser.build_parser(
    errata_state_opt, sa_type_opt, sa_filter_entry_opt, page_opt, limit_opt, sort_opt
)
sa_manage_args = parser.build_parser(manage_user, dry_run)
change_history_args = parser.build_parser(
    input_val_opt,
    manage_user_opt,
    chngs_module_opt,
    chngs_change_type_opt,
    event_start_date_opt,
    event_end_date_opt,
    page_opt,
    limit_opt,
    sort_opt,
)
comments_list_args = parser.build_parser(entity_type, entity_link)
default_reasons_list_args = parser.build_parser(
    default_reason_text_opt,
    default_reason_source_opt,
    default_reason_action_list_opt,
    default_reason_is_active_opt,
    page_opt,
    limit_opt,
    sort_opt,
)
vuln_status_list_args = parser.build_parser(
    vuln_status_input_val_opt,
    vuln_status_status_opt,
    vuln_status_resolution_opt,
    page_opt,
    limit_opt,
    sort_opt,
)
errata_user_tag_args = parser.build_parser(user_name_input, limit_opt)
errata_user_info_args = parser.build_parser(user_name)
errata_user_last_activities_args = parser.build_parser(user_name, limit_opt)
errata_user_aliases_get_args = parser.build_parser(user_name_opt)
errata_user_aliases_post_args = parser.build_parser(user_name, user_aliases_opt)
errata_user_subscriptions_args = parser.build_parser(user_name)
errata_user_tracking_args = parser.build_parser(
    user_name,
    manual_errata_changes_opt,
    tracking_input_opt,
    tracking_type_opt,
    tracking_action_opt,
    subscribed_start_date,
    subscribed_end_date,
    page_opt,
    limit_opt,
    sort_opt,
)
