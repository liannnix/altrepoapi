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

all_pkgsets_el_model = ns.model(
    "DependenciesAllPackagasetsElementModel",
    {
        "branch": fields.String(description="package set name"),
        "count": fields.Integer(description="number of source packages"),
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
        "dp_types": fields.List(fields.String, description="list of dependency types"),
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
        "summary": fields.String(description="package summary"),
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
            description="list of source packages of binary packages that "
            "provides required dependencies",
            as_list=True,
        ),
    },
)

backport_helper_el_model = ns.model(
    "BackportHelperBinaryElementModel",
    {
        "srpm": fields.String(description="package srpm"),
        "name": fields.String(description="package name"),
        "epoch": fields.Integer(description="package epoch"),
        "version": fields.String(description="package version"),
        "release": fields.String(description="package release"),
        "arch": fields.String(description="packages arch"),
    },
)
backport_helper_depth_el_model = ns.model(
    "BackportHelperBinaryDepthElementModel",
    {
        "depth": fields.Integer(description="dependency depth"),
        "packages": fields.Nested(
            backport_helper_el_model,
            description="packages dependencies list",
            as_list=True,
        ),
    },
)
backport_helper_model = ns.model(
    "BackportHelperModel",
    {
        "request_args": fields.Raw(description="request arguments"),
        "count": fields.Integer(description="number of packages found"),
        "maxdepth": fields.Integer(description="maxium depth reached"),
        "dependencies": fields.Nested(
            backport_helper_depth_el_model,
            description="packages dependencies list by depth",
            as_list=True,
        ),
    },
)

pkg_depends_el_model = ns.model(
    "PackageDependsElementModel",
    {
        "pkghash": fields.String(description="package hash UInt64 as string"),
        "name": fields.String(description="package name"),
        "arch": fields.String(description="package architecture"),
        "dp_name": fields.String(description="the name of the dependent package"),
        "dp_version": fields.String(description="the version of the dependent package"),
        "dp_flag": fields.Integer(description="dependency flag"),
        "dp_flag_decoded": fields.List(
            fields.String, description="decoded dependency flag"
        ),
    },
)
pkg_depends_model = ns.model(
    "PackageDependsModel",
    {
        "requires": fields.Nested(
            pkg_depends_el_model, description="package requirements"
        ),
        "provides": fields.Nested(pkg_depends_el_model, description="package provides"),
    },
)
pkg_build_dep_el_model = ns.model(
    "PackageBuildDependencyElementModel",
    {
        "pkghash": fields.String(description="source package hash UInt64 as string"),
        "name": fields.String(description="source package name"),
        "branch": fields.String(description="package set name"),
        "buildtime": fields.String(description="source package buildtime"),
        "acl": fields.List(fields.String, description="package ACL list"),
        "depends": fields.Nested(
            pkg_depends_model, description="package dependencies list", as_list=True
        ),
    },
)
pkg_build_dep_model = ns.model(
    "PackageBuildDependencyModel",
    {
        "request_args": fields.Raw(description="request arguments"),
        "length": fields.Integer(description="number of packages found"),
        "dependencies": fields.Nested(
            pkg_build_dep_el_model, description="build dependency results", as_list=True
        ),
    },
)

fast_deps_search_el_model = ns.model(
    "FastDependencySearchElementModel",
    {"dp_name": fields.String(description="the name of the dependent package")},
)
fast_deps_search_model = ns.model(
    "FastDependencySearchModel",
    {
        "request_args": fields.Raw(description="request arguments"),
        "length": fields.Integer(description="number of dependencies found"),
        "dependencies": fields.Nested(
            fast_deps_search_el_model, description="dependency list", as_list=True
        ),
    },
)
