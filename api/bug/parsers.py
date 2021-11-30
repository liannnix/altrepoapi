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

from api.base import parser

package_name = parser.register_item(
    "package_name",
    type=str,
    required=True,
    help="source or binary package name",
    location="args",
)
package_type_opt = parser.register_item(
    "package_type",
    type=str,
    choices=("source", "binary"),
    default="source",
    required=False,
    help="packages type [source|binary]",
    location="args",
)
maintainer_nickname = parser.register_item(
    "maintainer_nickname",
    type=str,
    required=True,
    help="maintainer nickname",
    location="args",
)

package_bugzilla_args = parser.build_parser(package_name, package_type_opt)
maintainer_bugzilla_args = parser.build_parser(maintainer_nickname)
