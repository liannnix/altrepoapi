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

from flask_restx import fields

from .namespace import get_namespace

ns = get_namespace()


all_iso_element_model = ns.model(
    "ImageAllISOElementModel",
    {
        "name": fields.String(description="ISO image package set name"),
        "date": fields.DateTime(description="ISO image package set date"),
        "uuid": fields.String(description="ISO image package set UUID"),
    },
)
all_iso_model = ns.model(
    "ImageAllISOModel",
    {
        "length": fields.Integer(description="number of ISO images"),
        "images": fields.Nested(
            all_iso_element_model,
            description="list of ISO images package sets information",
            as_list=True,
        ),
    },
)

iso_image_comp_model = ns.model(
    "ISOImageComponentModel",
    {
        "name": fields.String(description="ISO component name"),
        "date": fields.DateTime(description="ISO component package set date"),
        "uuid": fields.String(description="ISO component package set UUID"),
        "depth": fields.Integer(description="ISO component package set depth"),
        "type": fields.String(description="ISO component type", attribute="type_"),
        "class": fields.String(description="ISO component class", attribute="class_"),
        "size": fields.Integer(description="ISO component size"),
        "size_readable": fields.String(description="ISO component type (human readable)"),
        "json": fields.Raw(description="ISO component JSON data"),
    },
)
iso_image_el_model = ns.model(
    "ISOImageElementModel",
    {
        "name": fields.String(description="ISO image package set name"),
        "date": fields.DateTime(description="ISO image package set date"),
        "uuid": fields.String(description="ISO image package set UUID"),
        "components": fields.Nested(
            iso_image_comp_model,
            description="list of ISO image components information",
            as_list=True,
        ),
    },
)
iso_image_model = ns.model(
    "ISOImageModel",
    {
        "length": fields.Integer(description="number of ISO images"),
        "images": fields.Nested(
            iso_image_el_model,
            description="list of ISO images information",
            as_list=True,
        ),
    },
)
