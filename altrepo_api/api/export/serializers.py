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


repology_export_branch_stat_el_model = ns.model(
    "RepologyExportBranchStatElementModel",
    {
        "arch": fields.String(description="source package arch"),
        "count": fields.Integer(
            attribute="cnt",
            description="count of source packages by binary packages arch",
        ),
    },
)
repology_export_bin_pkg_el_model = ns.model(
    "RepologyExportBranchBinaryPackageElementModel",
    {
        "name": fields.String(description="package name"),
        "epoch": fields.Integer(description="package epoch"),
        "version": fields.String(description="package version"),
        "release": fields.String(description="package release"),
        "summary": fields.String(description="package summary"),
        "archs": fields.List(fields.String, description="package archs"),
    },
)
repology_export_src_pkg_el_model = ns.model(
    "RepologyExportBranchSourcePackageElementModel",
    {
        "name": fields.String(description="package name"),
        "epoch": fields.Integer(description="package epoch"),
        "version": fields.String(description="package version"),
        "release": fields.String(description="package release"),
        "url": fields.String(description="package upstream URL"),
        "license": fields.String(description="package license"),
        "category": fields.String(description="package category"),
        "summary": fields.String(description="package summary"),
        "packager": fields.String(description="packager email"),
        "homepage": fields.String(description="package homepage"),
        "recipe": fields.String(description="package spec file"),
        "recipe_raw": fields.String(description="package spec file raw"),
        "bugzilla": fields.String(description="package bugs"),
        "CPE": fields.String(description="package CPE"),
        "binaries": fields.Nested(
            repology_export_bin_pkg_el_model,
            description="binary packages info",
            as_list=True,
        ),
    },
)
repology_export_model = ns.model(
    "RepologyExportModel",
    {
        "branch": fields.String(description="package set name"),
        "date": fields.String(description="package set commit date"),
        "stats": fields.Nested(
            repology_export_branch_stat_el_model,
            description="package set stats",
            as_list=True,
        ),
        "packages": fields.Nested(
            repology_export_src_pkg_el_model,
            description="source packages info",
            as_list=True,
        ),
    },
)
