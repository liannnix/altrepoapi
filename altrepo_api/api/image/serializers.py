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

from tokenize import String
from flask_restx import fields

from .namespace import get_namespace

ns = get_namespace()


all_iso_element_model = ns.model(
    "ImageAllISOElementModel",
    {
        "branch": fields.String(description="ISO image base branch"),
        "name": fields.String(description="ISO image package set name"),
        "tag": fields.String(description="ISO image package set tag"),
        "file": fields.String(description="ISO image file name"),
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
        "size": fields.String(
            description="ISO component size (human readable)", attribute="image_size"
        ),
        "packages": fields.Integer(
            description="ISO component packages count", attribute="pkg_count"
        ),
        "uuid": fields.String(description="ISO component package set UUID"),
        "ruuid": fields.String(description="ISO component package set root UUID"),
        "kv": fields.Raw(description="ISO component metadata"),
    },
)
iso_image_el_model = ns.model(
    "ISOImageElementModel",
    {
        "date": fields.DateTime(description="ISO image package set date"),
        "uuid": fields.String(description="ISO image package set UUID"),
        "tag": fields.String(description="ISO image package set tag"),
        "branch": fields.String(description="ISO image base branch"),
        "edition": fields.String(description="ISO image edition"),
        "flavor": fields.String(description="ISO image flavor"),
        "platform": fields.String(description="ISO image platform"),
        "release": fields.String(description="ISO image release type"),
        "version_major": fields.Integer(description="ISO image version major"),
        "version_minor": fields.Integer(description="ISO image version minor"),
        "version_sub": fields.Integer(description="ISO image version sub"),
        "arch": fields.String(description="ISO image architecture"),
        "variant": fields.String(description="ISO image variant"),
        "type": fields.String(description="Image type"),
        "file": fields.String(description="ISO image file name"),
        "url": fields.List(fields.String(description="download URL")),
        "md5sum": fields.String(description="Image MD5 checksum"),
        "gost12sum": fields.String(description="Image GOST12 checksum"),
        "sha256sum": fields.String(description="Image SHA256 checksum"),
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
        "request_args": fields.Raw(description="request arguments"),
        "length": fields.Integer(description="number of ISO images"),
        "images": fields.Nested(
            iso_image_el_model,
            description="list of ISO images information",
            as_list=True,
        ),
    },
)
