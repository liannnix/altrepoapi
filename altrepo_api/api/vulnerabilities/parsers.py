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

from flask_restx import inputs

from altrepo_api.api.parser import (
    parser,
    cve_id_type,
    cve_id_list_type,
    bdu_id_type,
    bdu_id_list_type,
    ghsa_id_type,
    ghsa_id_list_type,
    vuln_id_type,
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
ghsa_id = parser.register_item(
    "vuln_id",
    type=ghsa_id_type,
    required=True,
    help="GHSA id",
    location="args",
)
ghsa_id_list = parser.register_item(
    "vuln_id",
    type=ghsa_id_list_type,
    action="split",
    required=True,
    help="GHSA id",
    location="args",
)
vuln_id = parser.register_item(
    "vuln_id",
    type=vuln_id_type,
    required=True,
    help="Vuln id",
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
exclude_json_opt = parser.register_item(
    "exclude_json",
    type=inputs.boolean,
    default=False,
    required=False,
    help="exclude vulnerability raw JSON from results",
    location="args",
)


cve_info_args = parser.build_parser(cve_id, exclude_json_opt)
bdu_info_args = parser.build_parser(bdu_id, exclude_json_opt)
ghsa_info_args = parser.build_parser(ghsa_id, exclude_json_opt)
vuln_info_args = parser.build_parser(vuln_id)
cve_vulnerable_packages_args = parser.build_parser(cve_id_list, branch)
bdu_vulnerable_packages_args = parser.build_parser(bdu_id_list, branch)
package_vulnerabilities_args = parser.build_parser(pkg_name, branch)
branch_vulnerabilities_args = parser.build_parser(branch)
maintainer_vulnerabilities_args = parser.build_parser(
    branch, maintainer_nick, by_acl_opt
)
