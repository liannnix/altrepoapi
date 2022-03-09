# ALTRepo API
# Copyright (C) 2021-2022  BaseALT Ltd

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
    image_version_type,
    img_edition_type,
    img_arch_type,
    img_release_type,
    img_variant_type,
    img_component_type,
    img_type,
)

# register items
branch = parser.register_item(
    "branch",
    type=branch_name_type,
    required=True,
    help="name of packageset",
    location="args",
)
img_edition_opt = parser.register_item(
    "edition",
    type=img_edition_type,
    required=False,
    help="Image edition",
    location="args",
)
img_release_opt = parser.register_item(
    "release",
    type=img_release_type,
    required=False,
    help="Image release type",
    location="args",
)
img_version_opt = parser.register_item(
    "version",
    type=image_version_type,
    required=False,
    help="Image version",
    location="args",
)
img_variant_opt = parser.register_item(
    "variant",
    type=img_variant_type,
    required=False,
    help="Image variant",
    location="args",
)
img_arch_opt = parser.register_item(
    "arch",
    type=img_arch_type,
    required=False,
    help="Image architecture",
    location="args",
)
img_component_opt = parser.register_item(
    "component",
    type=img_component_type,
    required=False,
    help="Image component",
    location="args",
)
img_type_opt = parser.register_item(
    "type",
    type=img_type,
    required=False,
    help="Image type",
    location="args",
)

# build parsers
image_info_args = parser.build_parser(
    branch,
    img_edition_opt,
    img_version_opt,
    img_release_opt,
    img_variant_opt,
    img_arch_opt,
    img_component_opt,
    img_type_opt
)
image_tag_args = parser.build_parser(branch, img_edition_opt)
