# altrepodb API
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

package_info_changelog_el_model = ns.model(
    "SitePackageInfoChangelogElementModel",
    {
        "date": fields.String(description="changelog date"),
        "name": fields.String(description="changelog name"),
        "evr": fields.String(description="changelog EVR"),
        "message": fields.String(description="changelog message"),
    },
)
package_versions_el_model = ns.model(
    "SitePackageVersionsElementModel",
    {
        "branch": fields.String(description="package set name"),
        "version": fields.String(description="package version"),
        "release": fields.String(description="package release"),
        "pkghash": fields.String(description="package hash UInt64 as string"),
    },
)
package_beehive_el_model = ns.model(
    "SitePackageBeehiveElementModel",
    {
        "arch": fields.String(description="Beehive rebuild arch"),
        "status": fields.String(description="Beehive rebuild status"),
        "updated": fields.String(description="Beehive rebuild date"),
        "build_time": fields.Float(
            description="Beehive package build elapsed (seconds)"
        ),
        "ftbfs_since": fields.String(description="Package FTBFS since date"),
        "url": fields.String(description="Beehive package build error log URL"),
    },
)
package_info_tasks_el_model = ns.model(
    "SitePackageTasksElementModel",
    {
        "type": fields.String(description="task type"),
        "id": fields.String(description="task id"),
    },
)
package_dependencies_el_model = ns.model(
    "SitePackageDependenciesElementModel",
    {
        "name": fields.String(description="the name of the dependent package"),
        "version": fields.String(description="the version of the dependent package"),
        "type": fields.String(description="dependency type"),
        "flag": fields.Integer(description="dependency flag"),
        "flag_decoded": fields.List(
            fields.String, description="decoded dependency flag"
        ),
    },
)
package_dependencies_model = ns.model(
    "SitePackageDependenciesModel",
    {
        "request_args": fields.Raw(description="request arguments"),
        "length": fields.Integer(description="number of dependencies found"),
        "dependencies": fields.Nested(
            package_dependencies_el_model,
            description="unpackaged directories information",
            as_list=True,
        ),
        "versions": fields.Nested(
            package_versions_el_model, as_list=True, description="all package versions"
        ),
    },
)
package_info_archs_el_model = ns.model(
    "SitePackageInfoArchsModel",
    {
        "name": fields.String(description="package name"),
        "archs": fields.List(fields.String, description="package arches"),
        "pkghash": fields.List(
            fields.String, description="package hash UInt64 as string"
        ),
    },
)
package_info_model = ns.model(
    "SitePackageInfoModel",
    {
        "pkghash": fields.String(description="package hash UInt64 as string"),
        "request_args": fields.Raw(description="request arguments"),
        "name": fields.String(description="package name"),
        "version": fields.String(description="package version"),
        "release": fields.String(description="package release"),
        "arch": fields.String(description="package arch"),
        "buildtime": fields.Integer(description="package build time"),
        "task": fields.Integer(description="package build task"),
        "gear": fields.String(description="package task gear type"),
        "license": fields.String(description="package license"),
        "category": fields.String(description="package group"),
        "url": fields.String(description="package url"),
        "summary": fields.String(description="package summary"),
        "description": fields.String(description="package description"),
        "packager": fields.String(description="package packager name"),
        "packager_nickname": fields.String(description="package packager nickname"),
        "acl": fields.List(fields.String, description="binary packages"),
        "maintainers": fields.List(
            fields.String, description="all maintainer's nicknames"
        ),
        "package_archs": fields.Nested(
            package_info_archs_el_model,
            as_list=True,
            description="List of source or binary packages by archs",
        ),
        "tasks": fields.Nested(
            package_info_tasks_el_model, as_list=True, description="package tasks"
        ),
        "changelog": fields.Nested(
            package_info_changelog_el_model,
            as_list=True,
            description="package changelog",
        ),
        "versions": fields.Nested(
            package_versions_el_model, as_list=True, description="all package versions"
        ),
        "beehive": fields.Nested(
            package_beehive_el_model, as_list=True, description="Beehive rebuild status"
        ),
        "dependencies": fields.Nested(
            package_dependencies_el_model,
            as_list=True,
            description="all the dependence of the package",
        ),
    },
)


package_chlog_el_model = ns.model(
    "SiteChangelogElementModel",
    {
        "date": fields.String(description="changelog date"),
        "name": fields.String(description="changelog name"),
        "evr": fields.String(description="changelog EVR"),
        "message": fields.String(description="changelog message"),
    },
)
package_chlog_model = ns.model(
    "SiteChangelogModel",
    {
        "pkghash": fields.String(description="package hash UInt64 as string"),
        "request_args": fields.Raw(description="request arguments"),
        "length": fields.Integer(description="number changelog records"),
        "changelog": fields.Nested(
            package_chlog_el_model, description="package changelog", as_list=True
        ),
    },
)


deleted_package_model = ns.model(
    "SiteDeletedPackageModel",
    {
        "branch": fields.String(description="package set name"),
        "package": fields.String(description="package name"),
        "version": fields.String(description="package version"),
        "release": fields.String(description="package release"),
        "hash": fields.String(description="package hash UInt64 as string"),
        "task_id": fields.Integer(description="task id"),
        "subtask_id": fields.Integer(description="subtask id"),
        "task_owner": fields.String(description="task created by"),
        "subtask_owner": fields.String(
            attribute="subtask_userid", description="subtask created by"
        ),
        "task_changed": fields.String(description="task completed at"),
        "task_message": fields.String(description="task message"),
    },
)


last_pkgs_with_cve_fix_el_model = ns.model(
    "SiteLastPackagesWithCVEFixesElementModel",
    {
        "hash": fields.String(description="package hash UInt64 as string"),
        "name": fields.String(description="package name"),
        "version": fields.String(description="package version"),
        "release": fields.String(description="package release"),
        "summary": fields.String(description="package summary"),
        "buildtime": fields.Integer(description="package buildtime"),
        "changelog_date": fields.String(
            description="package last changelog date (ISO 8601 format)"
        ),
        "changelog_text": fields.String(description="package last changelog text"),
    },
)
last_pkgs_with_cve_fix_model = ns.model(
    "SiteLastPackagesWithCVEFixesModel",
    {
        "request_args": fields.Raw(description="request arguments"),
        "length": fields.Integer(description="number of packages found"),
        "packages": fields.Nested(
            last_pkgs_with_cve_fix_el_model,
            description="last packages with CVE fixes information",
            as_list=True,
        ),
    },
)


package_downloads_pkg_model = ns.model(
    "SitePackagesDownloadsPackageModel",
    {
        "name": fields.String(description="package name"),
        "url": fields.String(description="package download link"),
        "md5": fields.String(description="package MD5 checksum"),
        "size": fields.String(description="human readable package file size"),
    },
)
package_downloads_el_model = ns.model(
    "SitePackagesDownloadsElementModel",
    {
        "arch": fields.String(description="package architecture"),
        "packages": fields.Nested(
            package_downloads_pkg_model,
            description="Packages downloads",
            as_list=True,
        ),
    },
)
package_downloads_model = ns.model(
    "SitePackagesDownloadsModel",
    {
        "pkghash": fields.String(description="package hash UInt64 as string"),
        "request_args": fields.Raw(description="request arguments"),
        "downloads": fields.Nested(
            package_downloads_el_model,
            description="Packages downloads",
            as_list=True,
        ),
        "versions": fields.Nested(
            package_versions_el_model,
            description="Packages downloads",
            as_list=True,
        ),
    },
)


pkgs_binary_list_el_model = ns.model(
    "SitePackagesBinaryListElementModel",
    {
        "hash": fields.String(description="package hash UInt64 as string"),
        "name": fields.String(description="package name"),
        "version": fields.String(description="package version"),
        "release": fields.String(description="package release"),
        "arch": fields.String(description="package arch"),
    },
)
pkgs_binary_list_model = ns.model(
    "SitePackagesBinaryListModel",
    {
        "request_args": fields.Raw(description="request arguments"),
        "length": fields.Integer(description="number of packages found"),
        "packages": fields.Nested(
            pkgs_binary_list_el_model,
            description="binary packages list",
            as_list=True,
        ),
        "versions": fields.Nested(
            package_versions_el_model, as_list=True, description="all package versions"
        ),
    },
)


bin_package_scripts_el_model = ns.model(
    "SiteBinPackageScriptsElementModel",
    {
        "postin": fields.String(description="post install script"),
        "postun": fields.String(description="post uninstall script"),
        "prein": fields.String(description="pre install script"),
        "preun": fields.String(description="pre uninstall script"),
    },
)
depends_packages_model = ns.model(
    "SiteBinPackageScriptsModel",
    {
        "request_args": fields.Raw(description="request arguments"),
        "pkg_name": fields.String(description="package name"),
        "pkg_arch": fields.String(description="package arch"),
        "length": fields.Integer(description="number of scripts found"),
        "scripts": fields.Nested(
            bin_package_scripts_el_model,
            description="unpackaged directories information",
            as_list=True,
        ),
        "versions": fields.Nested(
            package_versions_el_model, as_list=True, description="all package versions"
        ),
    },
)


src_pkgs_versions_model = ns.model(
    "SiteSourcePackagesVersionsModel",
    {
        "request_args": fields.Raw(description="request arguments"),
        "versions": fields.Nested(
            package_versions_el_model,
            description="Packages downloads",
            as_list=True,
        ),
    },
)


bin_package_log_el_model = ns.model(
    "BinPackageLogElementModel",
    {
        "pkg_hash": fields.String(description="binary package hash"),
        "task_id": fields.Integer(description="task id"),
        "subtask_id": fields.Integer(description="subtask id"),
        "subtask_arch": fields.String(description="package architecture"),
        "buildlog_hash": fields.String(description="hash of the log"),
        "link": fields.String(description="link to the binary package build log")
    }
)
