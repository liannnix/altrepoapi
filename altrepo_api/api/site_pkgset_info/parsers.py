# ALTRepo API
# Copyright (C) 2021  BaseALT Ltd

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

from altrepo_api.api.base import parser

branch = parser.register_item(
    "branch", type=str, required=True, help="name of packageset", location="args"
)
package_type = parser.register_item(
    "package_type",
    type=str,
    choices=("all", "source", "binary"),
    default="source",
    required=False,
    help="packages type [source|binary|all]",
    location="args",
)

all_archs_args = parser.build_parser(branch)
pkgset_categories_args = parser.build_parser(branch, package_type)
