# ALTRepo API
# Copyright (C) 2021-2025  BaseALT Ltd

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
        "CPE": fields.List(fields.String(description="package CPE"), attribute="cpe"),
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

sitemap_packages_el_model = ns.model(
    "SitemapPackagesElementModel",
    {
        "pkghash": fields.String(description="package hash UInt64 as string"),
        "name": fields.String(description="package name"),
        "buildtime": fields.Integer(description="package buildtime"),
    },
)
sitemap_packages_export_model = ns.model(
    "SitemapPackagesExportModel",
    {
        "branch": fields.String(description="package set name"),
        "packages": fields.Nested(
            sitemap_packages_el_model,
            description="source packages info",
            as_list=True,
        ),
    },
)

pkgset_packages_export_el_model = ns.model(
    "PackagesetPackagesExportElementModel",
    {
        "name": fields.String(description="package name"),
        "epoch": fields.Integer(description="package epoch"),
        "version": fields.String(description="package version"),
        "release": fields.String(description="package release"),
        "arch": fields.String(description="package arch"),
        "disttag": fields.String(description="package disttag"),
        "buildtime": fields.Integer(description="package build time"),
        "source": fields.String(description="source package name"),
    },
)
pkgset_packages_export_model = ns.model(
    "PackagesetPackagesExportModel",
    {
        "request_args": fields.Raw(description="request arguments"),
        "length": fields.Integer(description="number of binary packages found"),
        "packages": fields.Nested(
            pkgset_packages_export_el_model,
            description="binary packages information",
            as_list=True,
        ),
    },
)


branch_tree_task_model = ns.model(
    "BranchTreeTaskModel",
    {
        "id": fields.Integer(description="task ID"),
        "prev": fields.Integer(description="previous task ID"),
        "branch": fields.String(description="task branch name"),
        "date": fields.String(description="task build time"),
    },
)
branch_tree_branch_commit_model = ns.model(
    "BranchTreeBranchCommitModel",
    {
        "name": fields.String(description="branch name"),
        "date": fields.String(description="branch commit date"),
        "task": fields.Integer(description="task ID"),
    },
)
branch_tree_branch_point_model = ns.model(
    "BranchTreeBranchPointModel",
    {
        "branch": fields.String(description="branch name"),
        "task": fields.Nested(branch_tree_task_model, description="first branch' task"),
        "from_task": fields.Nested(
            branch_tree_task_model, description="task from parent branch"
        ),
    },
)
branch_tree_model = ns.model(
    "BranchTreeModel",
    {
        "branches": fields.List(fields.String, description="list of branches"),
        "tasks": fields.Nested(
            branch_tree_task_model, description="branches tasks list", as_list=True
        ),
        "branch_commits": fields.Nested(
            branch_tree_branch_commit_model,
            description="branches commits list",
            as_list=True,
        ),
        "branch_points": fields.Nested(
            branch_tree_branch_point_model,
            description="branch points list",
            as_list=True,
        ),
    },
)

beehive_ftbfs_el_model = ns.model(
    "ExportBeehiveFTBFSElementModel",
    {
        "branch": fields.String(description="Beehive branch"),
        "hash": fields.String(description="package hash"),
        "name": fields.String(description="package name"),
        "epoch": fields.Integer(description="package epoch"),
        "version": fields.String(description="package version"),
        "release": fields.String(description="package release"),
        "arch": fields.String(description="Beehive arch"),
        "updated": fields.String(description="Beehive rebuild date"),
        "ftbfs_since": fields.String(description="Package FTBFS since date"),
        "url": fields.String(description="Beehive package build error log URL"),
    },
)
beehive_ftbfs_list_model = ns.model(
    "ExportBeehiveFTBFSListModel",
    {
        "request_args": fields.Raw(description="request arguments"),
        "length": fields.Integer(description="number of packages found"),
        "ftbfs": fields.Nested(
            beehive_ftbfs_el_model,
            description="Beehive packages rebuild errors",
            as_list=True,
        ),
    },
)
