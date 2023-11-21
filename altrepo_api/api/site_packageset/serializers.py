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


pkgset_packages_el_model = ns.model(
    "SitePackagesElementModel",
    {
        "hash": fields.String(description="package hash UInt64 as string"),
        "name": fields.String(description="package name"),
        "version": fields.String(description="package version"),
        "release": fields.String(description="package release"),
        "summary": fields.String(description="package summary"),
        "buildtime": fields.Integer(description="package buildtime"),
        "category": fields.String(description="package category"),
        "maintainer": fields.String(description="package maintainer"),
        "changelog": fields.String(description="package last changelog message"),
        "task_id": fields.Integer(description="package build task id"),
        "subtask_id": fields.Integer(description="package build subtask id"),
        "task_owner": fields.String(description="package build task owner"),
    },
)
pkgset_packages_model = ns.model(
    "SitePackagesModel",
    {
        "request_args": fields.Raw(description="request arguments"),
        "length": fields.Integer(description="number of packages found"),
        "subcategories": fields.List(
            fields.String, description="list of subcategories"
        ),
        "packages": fields.Nested(
            pkgset_packages_el_model,
            description="unpackaged directories information",
            as_list=True,
        ),
    },
)


pkgset_pkghash_model = ns.model(
    "SitePackagesetPackageHashModel",
    {
        "request_args": fields.Raw(description="request arguments"),
        "pkghash": fields.String(description="package hash UInt64 as string"),
        "version": fields.String(description="package version"),
        "release": fields.String(description="package release"),
    },
)


fing_pkgs_by_name_pkg_el_model = ns.model(
    "SitePackageVersionsElementModel",
    {
        "branch": fields.String(description="package set name"),
        "version": fields.String(description="package version"),
        "release": fields.String(description="package release"),
        "pkghash": fields.String(description="package hash UInt64 as string"),
        "deleted": fields.Boolean(description="package was deleted from branch"),
    },
)
fing_pkgs_by_name_pkg_model = ns.model(
    "SiteFingPackagesPackageModel",
    {
        "name": fields.String(description="package name"),
        "buildtime": fields.Integer(description="package build time"),
        "url": fields.String(description="package url"),
        "summary": fields.String(description="package summary"),
        "category": fields.String(description="package category"),
        "versions": fields.Nested(
            fing_pkgs_by_name_pkg_el_model,
            as_list=True,
            description="all package versions",
        ),
        "by_binary": fields.Boolean(description="found by binary package name"),
    },
)
fing_pkgs_by_name_model = ns.model(
    "SiteFingPackagesModel",
    {
        "request_args": fields.Raw(description="request arguments"),
        "length": fields.Integer(description="number of packages found"),
        "packages": fields.Nested(
            fing_pkgs_by_name_pkg_model, description="found packages", as_list=True
        ),
    },
)

fast_pkgs_search_el_model = ns.model(
    "SiteFastPackagesSearchElementModel",
    {
        "name": fields.String(description="package name"),
        "sourcepackage": fields.String(description="package type"),
        "branches": fields.List(fields.String, description="list of package branches"),
    },
)
fast_pkgs_search_model = ns.model(
    "SiteFastPackagesSearchModel",
    {
        "request_args": fields.Raw(description="request arguments"),
        "length": fields.Integer(description="number of packages found"),
        "packages": fields.Nested(
            fast_pkgs_search_el_model,
            description="list of found packages",
            as_list=True,
        ),
    },
)

pkgsets_by_hash_model = ns.model(
    "SitePackagesetsByHashModel",
    {
        "pkghash": fields.String(description="package hash UInt64 as string"),
        "length": fields.Integer(description="number of package sets found"),
        "branches": fields.List(fields.String, description="package sets"),
    },
)


last_packages_branch_pkg_model = ns.model(
    "SiteLastBranchPackagesPackageModel",
    {
        "hash": fields.String(description="package hash UInt64 as string"),
        "name": fields.String(attribute="pkg_name", description="package name"),
        "version": fields.String(
            attribute="pkg_version", description="package version"
        ),
        "release": fields.String(
            attribute="pkg_release", description="package release"
        ),
        "summary": fields.String(
            attribute="pkg_summary", description="package summary"
        ),
        "buildtime": fields.Integer(
            attribute="pkg_buildtime", description="last binary package buildtime"
        ),
        "changelog_name": fields.String(description="package last changelog name"),
        "changelog_nickname": fields.String(
            description="package last changelog nickname"
        ),
        "changelog_date": fields.String(
            description="package last changelog message date"
        ),
        "changelog_text": fields.String(description="package last changelog message"),
    },
)
last_packages_branch_model = ns.model(
    "SiteLastBranchPackagesModel",
    {
        "request_args": fields.Raw(description="request arguments"),
        "length": fields.Integer(description="number of packages found"),
        "packages": fields.Nested(
            last_packages_branch_pkg_model,
            description="last packages list",
            as_list=True,
        ),
        "last_branch_date": fields.String(description="last loaded branch date"),
    },
)

pkgset_pkghash_by_nvr_model = ns.model(
    "SitePackagesetPackageHashByNameVersionRelease",
    {
        "request_args": fields.Raw(description="request arguments"),
        "pkghash": fields.String(description="package hash UInt64 as string"),
    },
)

find_src_pkg_in_branch_model = ns.model(
    "FindSourcePackageInBranch",
    {
        "request_args": fields.Raw(description="request arguments"),
        "source_package": fields.String(description="source package name"),
    },
)
