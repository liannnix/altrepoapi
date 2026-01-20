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

from flask_restx import fields

from .namespace import get_namespace

ns = get_namespace()

license_tokens_el_model = ns.model(
    "LicenseTokensElementModel",
    {
        "token": fields.String(description="license token"),
        "license": fields.String(description="SPDX license ID"),
    },
)
license_tokens_model = ns.model(
    "LicenseTokensModel",
    {
        "request_args": fields.Raw(),
        "length": fields.Integer(description="number of tokens"),
        "tokens": fields.Nested(
            license_tokens_el_model,
            description="list of found valid license tokens",
            as_list=True,
        ),
    },
)


license_info_model = ns.model(
    "LicenseInfoModel",
    {
        "request_args": fields.Raw(),
        "id": fields.String(description="SPDX license ID"),
        "name": fields.String(description="SPDX license name"),
        "text": fields.String(description="license text"),
        "type": fields.String(description="license type"),
        "header": fields.String(description="license header"),
        "comment": fields.String(description="license comment"),
        "urls": fields.List(fields.String(description="license URLs")),
    },
)
