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

from altrepo_api.api.parser import (
    parser,
    branch_name_type,
    pkg_name_type,
    img_edition_type,
    img_type,
)


# base arg parser items
name = parser.register_item(
    "name", type=pkg_name_type, required=True, help="package name", location="args"
)
branch = parser.register_item(
    "branch",
    type=branch_name_type,
    required=True,
    help="image base branch",
    location="args",
)
img_edition = parser.register_item(
    "edition",
    type=img_edition_type,
    required=True,
    help="image edition",
    location="args",
)
image_type = parser.register_item(
    "type",
    type=img_type,
    required=True,
    help="image type",
    location="args",
)

# build parsesr
pkgs_versions_from_images_args = parser.build_parser(
    name, branch, img_edition, image_type
)
