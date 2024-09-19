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
    cve_id_type,
    cve_id_list_type,
    bdu_id_type,
    bdu_id_list_type,
    branch_name_type,
    maintainer_nick_type,
    pkg_name_type,
)

cve_id = parser.register_item(
    "vuln_id",
    type=cve_id_type,
    required=True,
    help="CVE id",
    location="args",
)
cve_id_list = parser.register_item(
    "vuln_id",
    type=cve_id_list_type,
    action="split",
    required=True,
    help="CVE id",
    location="args",
)
bdu_id = parser.register_item(
    "vuln_id",
    type=bdu_id_type,
    required=True,
    help="BDU id",
    location="args",
)
bdu_id_list = parser.register_item(
    "vuln_id",
    type=bdu_id_list_type,
    action="split",
    required=True,
    help="BDU id",
    location="args",
)
branch = parser.register_item(
    "branch",
    type=branch_name_type,
    required=True,
    help="branch",
    location="args",
)
pkg_name = parser.register_item(
    "name",
    type=pkg_name_type,
    required=True,
    help="package name",
    location="args",
)
by_acl_opt = parser.register_item(
    "by_acl",
    type=str,
    choices=(
        "none",
        "by_nick",
        "by_nick_leader",
        "by_nick_or_group",
        "by_nick_leader_and_group",
    ),
    default="none",
    required=False,
    help="search maintainer's packages by ACL",
    location="args",
)
maintainer_nick = parser.register_item(
    "maintainer_nickname",
    type=maintainer_nick_type,
    required=True,
    help="nickname of maintainer",
    location="args",
)

cve_info_args = parser.build_parser(cve_id)
bdu_info_args = parser.build_parser(bdu_id)
cve_vulnerable_packages_args = parser.build_parser(cve_id_list, branch)
bdu_vulnerable_packages_args = parser.build_parser(bdu_id_list, branch)
package_vulnerabilities_args = parser.build_parser(pkg_name, branch)
branch_vulnerabilities_args = parser.build_parser(branch)
maintainer_vulnerabilities_args = parser.build_parser(
    branch, maintainer_nick, by_acl_opt
)
