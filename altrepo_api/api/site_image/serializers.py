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

from flask_restx import fields

from .namespace import get_namespace

ns = get_namespace()

pkgs_versions_from_images_el__el_model = ns.model(
    "SiteImagePackageVersionsElementModel",
    {
        "tag": fields.String(description="image tag"),
        "uuid": fields.String(description="image root UUID"),
        "version_major": fields.Integer(description="Image version major"),
        "version_minor": fields.Integer(description="Image version minor"),
        "version_sub": fields.Integer(description="Image version sub"),
        "img_arch": fields.String(description="Image architecture"),
        "platform": fields.String(description="Image platform"),
        "variant": fields.String(description="Image variant"),
        "flavor": fields.String(attribute="img_flavor", description="Image flavor"),
        "type": fields.String(description="Image type"),
        "hash": fields.String(description="package hash UInt64 as string"),
        "name": fields.String(description="package name"),
        "version": fields.String(description="package version"),
        "release": fields.String(description="package release"),
        "arch": fields.String(description="package arch"),
    },
)
pkgs_versions_from_images_model = ns.model(
    "SiteImagePackageVersionsModel",
    {
        "request_args": fields.Raw(description="request arguments"),
        "length": fields.Integer(description="number of images found"),
        "versions": fields.Nested(
            pkgs_versions_from_images_el__el_model, as_list=True, description="all package versions"
        ),
    },
)
