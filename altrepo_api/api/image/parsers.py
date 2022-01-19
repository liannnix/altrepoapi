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

from altrepo_api.api.parser import (
    parser,
    branch_name_type,
    image_name_type,
    image_version_type,
    iso_edition_type,
    iso_arch_type,
    iso_release_type,
    iso_variant_type,
    iso_component_type,
)

# register items
branch = parser.register_item(
    "branch",
    type=branch_name_type,
    required=True,
    help="name of packageset",
    location="args",
)
iso_edition_opt = parser.register_item(
    "edition",
    type=iso_edition_type,
    required=False,
    help="ISO image edition",
    location="args",
)
iso_release_opt = parser.register_item(
    "release",
    type=iso_release_type,
    required=False,
    help="ISO image release type",
    location="args",
)
iso_version_opt = parser.register_item(
    "version",
    type=image_version_type,
    required=False,
    help="ISO image version",
    location="args",
)
iso_variant_opt = parser.register_item(
    "variant",
    type=iso_variant_type,
    required=False,
    help="ISO image variant",
    location="args",
)
iso_arch_opt = parser.register_item(
    "arch",
    type=iso_arch_type,
    required=False,
    help="ISO image architecture",
    location="args",
)
iso_component_opt = parser.register_item(
    "component",
    type=iso_component_type,
    required=False,
    help="ISO image component",
    location="args",
)

# build parsers
iso_images_args = parser.build_parser(
    branch,
    iso_edition_opt,
    iso_version_opt,
    iso_release_opt,
    iso_variant_opt,
    iso_arch_opt,
    iso_component_opt,
)
