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


all_pkgsets_el_model = ns.model(
    "DependenciesAllPackagasetsElementModel",
    {
        "branch": fields.String(description="package set name"),
        "count": fields.Integer(description="number of source packages"),
    },
)

package_versions_el_model = ns.model(
    "DependenciesPackageVersionsElementModel",
    {
        "branch": fields.String(description="package set name"),
        "version": fields.String(description="package version"),
        "release": fields.String(description="package release"),
        "pkghash": fields.String(description="package hash UInt64 as string"),
    },
)

package_dependencies_el_model = ns.model(
    "DependenciesPackageDependenciesElementModel",
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
    "DependenciesPackageDependenciesModel",
    {
        "request_args": fields.Raw(description="request arguments"),
        "length": fields.Integer(description="number of dependencies found"),
        "dependencies": fields.Nested(
            package_dependencies_el_model,
            description="package dependencies list",
            as_list=True,
        ),
        "versions": fields.Nested(
            package_versions_el_model, as_list=True, description="all package versions"
        ),
    },
)

depends_packages_el_model = ns.model(
    "DependenciesPackagesElementModel",
    {
        "hash": fields.String(description="package hash UInt64 as string"),
        "name": fields.String(description="package name"),
        "version": fields.String(description="package version"),
        "release": fields.String(description="package release"),
        "arch": fields.String(description="package arch"),
        "sourcepackage": fields.Integer(description="package type"),
        "summary": fields.String(description="package summary"),
        "buildtime": fields.Integer(description="package buildtime"),
        "category": fields.String(description="package category"),
        "maintainer": fields.String(description="package maintainer"),
    },
)
depends_packages_model = ns.model(
    "DependenciesPackagesModel",
    {
        "request_args": fields.Raw(description="request arguments"),
        "length": fields.Integer(description="number of packages found"),
        "packages": fields.Nested(
            depends_packages_el_model,
            description="package dependencies list",
            as_list=True,
        ),
        "branches": fields.Nested(
            all_pkgsets_el_model,
            description="list of package sets with binary package count",
            as_list=True,
        ),
    },
)

pkg_info_model = ns.model(
    "PackageInfoModel",
    {
        "name": fields.String(description="package name"),
        "epoch": fields.Integer(description="package epoch"),
        "version": fields.String(description="package version"),
        "release": fields.String(description="package release"),
        "buildtime": fields.Integer(description="package buildtime"),
    },
)

package_info_el_model = ns.model(
    "DependenciesPackageInfoElementModel",
    {
        "name": fields.String(description="package name"),
        "version": fields.String(description="package version"),
        "release": fields.String(description="package release"),
        "pkghash": fields.String(description="package hash UInt64 as string"),
    },
)
package_build_deps_model = ns.model(
    "DependenciesPackageBuildDependenciesModel",
    {
        "request_args": fields.Raw(description="request arguments"),
        "length": fields.Integer(description="number of packages found"),
        "package_info": fields.Nested(
            pkg_info_model, description="source package info"
        ),
        "dependencies": fields.Nested(
            package_dependencies_el_model,
            description="package dependencies list",
            as_list=True,
        ),
        "provided_by_src": fields.Nested(
            package_info_el_model,
            description="list of source packages of binary packages that provides required dependencies",
            as_list=True,
        ),
    },
)
