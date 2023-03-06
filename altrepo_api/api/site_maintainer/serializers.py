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

all_maintainers_el_model = ns.model(
    "AllMaintainersElementModel",
    {
        "packager_name": fields.String(description="Maintainer's name"),
        "packager_nickname": fields.String(description="Maintainer's nickname"),
        "count_source_pkg": fields.Integer(description="Number of source packages"),
    },
)
all_maintainers_model = ns.model(
    "AllMaintainersModel",
    {
        "request_args": fields.Raw(description="request arguments"),
        "length": fields.Integer(description="number of maintainers found"),
        "maintainers": fields.Nested(
            all_maintainers_el_model, description="maintainers info", as_list=True
        ),
    },
)


maintainer_info_model = ns.model(
    "MaintainerInfoModel",
    {
        "request_args": fields.Raw(description="request arguments"),
        "information": fields.Nested(
            all_maintainers_el_model, description="maintainers info"
        ),
    },
)


maintainer_pkgs_el_model = ns.model(
    "MaintainerPackagesElementModel",
    {
        "name": fields.String(description="package name"),
        "buildtime": fields.Integer(description="package build time"),
        "url": fields.String(description="package url"),
        "summary": fields.String(description="package summary"),
        "version": fields.String(description="package version"),
        "release": fields.String(description="package release"),
    },
)
maintainer_pkgs_model = ns.model(
    "MaintainerPackagesModel",
    {
        "request_args": fields.Raw(description="request arguments"),
        "length": fields.Integer(description="number of maintainers found"),
        "packages": fields.Nested(
            maintainer_pkgs_el_model, description="found packages", as_list=True
        ),
    },
)


all_pkgsets_el_model = ns.model(
    "SiteAllPackagasetsElementModel",
    {
        "branch": fields.String(description="package set name"),
        "count": fields.Integer(description="number of source packages"),
    },
)
maintainer_branches_model = ns.model(
    "MaintainerBranchesModel",
    {
        "request_args": fields.Raw(description="request arguments"),
        "length": fields.Integer(description="number of maintainers found"),
        "branches": fields.Nested(
            all_pkgsets_el_model,
            as_list=True,
            description="all branches of the maintainer",
        ),
    },
)


repocop_by_maintainer_el_model = ns.model(
    "RepocopByMaintainerElementModel",
    {
        "pkg_name": fields.String(description="package name"),
        "pkg_version": fields.String(description="package version"),
        "pkg_release": fields.String(description="package release"),
        "pkg_arch": fields.String(description="package arch"),
        "srcpkg_name": fields.String(description="source package name"),
        "branch": fields.String(description="repocop branch"),
        "test_name": fields.String(description="repocop test name"),
        "test_status": fields.String(description="repocop test status"),
        "test_message": fields.String(description="repocop test message"),
        "test_date": fields.DateTime(description="repocop test date"),
    },
)
repocop_by_maintainer_model = ns.model(
    "RepocopByMaintainerModel",
    {
        "request_args": fields.Raw(description="request arguments"),
        "length": fields.Integer(description="number of packages found"),
        "packages": fields.Nested(
            repocop_by_maintainer_el_model,
            description="repocop packages info",
            as_list=True,
        ),
    },
)


beehive_by_maintainer_el_model = ns.model(
    "SiteBeehiveByMaintainerElementModel",
    {
        "branch": fields.String(description="Beehive branch"),
        "name": fields.String(description="package name"),
        "version": fields.String(description="package version"),
        "release": fields.String(description="package release"),
        "arch": fields.String(description="Beehive arch"),
        "updated": fields.String(description="Beehive rebuild date"),
        "ftbfs_since": fields.String(description="Package FTBFS since date"),
        "build_time": fields.Float(
            description="Beehive package build elapsed (seconds)"
        ),
        "url": fields.String(description="Beehive package build error log URL"),
    },
)
beehive_by_maintainer_model = ns.model(
    "SiteBeehiveByMaintainerModel",
    {
        "request_args": fields.Raw(description="request arguments"),
        "length": fields.Integer(description="number of packages found"),
        "beehive": fields.Nested(
            beehive_by_maintainer_el_model,
            description="Beehive packages rebuild errors",
            as_list=True,
        ),
    },
)


watch_by_maintainer_el_model = ns.model(
    "SiteWatchByMaintainerElementModel",
    {
        "pkg_name": fields.String(description="package name"),
        "old_version": fields.String(description="old package version"),
        "new_version": fields.String(description="new package version"),
        "url": fields.String(description="url for download src"),
        "date_update": fields.String(description="Watch update date"),
    },
)
watch_by_maintainer_model = ns.model(
    "SiteWatchByMaintainerModel",
    {
        "request_args": fields.Raw(description="request arguments"),
        "length": fields.Integer(description="number of packages found"),
        "packages": fields.Nested(
            watch_by_maintainer_el_model,
            description="found packages",
            as_list=True,
        ),
    },
)
