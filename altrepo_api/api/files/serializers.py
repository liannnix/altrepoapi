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

from flask_restx import fields

from .namespace import get_namespace

ns = get_namespace()


files_el_model = ns.model(
    "FilesElementModel",
    {
        "file_name": fields.String(description="file name"),
        "file_hashname": fields.String(description="hash from the filename"),
        "file_class": fields.String(description="file class"),
        "symlink": fields.String(description="link path"),
        "file_mode": fields.String(
            description="file permissions string representation"
        ),
    },
)
files_model = ns.model(
    "FilesModel",
    {
        "request_args": fields.Raw(description="request arguments"),
        "length": fields.Integer(description="number of files found"),
        "files": fields.Nested(
            files_el_model, description="file list", as_list=True
        ),
    },
)

fast_file_search_el_model = ns.model(
    "FastFileSearchElementModel",
    {
        "file_name": fields.String(description="file name")
    },
)
fast_file_search_model = ns.model(
    "FastFileSearchModel",
    {
        "request_args": fields.Raw(description="request arguments"),
        "length": fields.Integer(description="number of files found"),
        "files": fields.Nested(
            fast_file_search_el_model, description="file list", as_list=True
        ),
    },
)

packages_by_el_model = ns.model(
    "PackagesByFileElementModel",
    {
        "hash": fields.String(description="package hash UInt64 as string"),
        "name": fields.String(description="package name"),
        "version": fields.String(description="package version"),
        "release": fields.String(description="package release"),
        "arch": fields.String(description="package architecture"),
    },
)
packages_by_model = ns.model(
    "PackagesByFileModel",
    {
        "request_args": fields.Raw(description="request arguments"),
        "length": fields.Integer(description="number of package found"),
        "packages": fields.Nested(
            packages_by_el_model, description="package list", as_list=True
        ),
    },
)

