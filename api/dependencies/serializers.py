from flask_restx import fields

from api.dependencies.dependencies import ns


all_pkgsets_el_model = ns.model(
    "SiteAllPackagasetsElementModel",
    {
        "branch": fields.String(description="package set name"),
        "count": fields.Integer(description="number of source packages"),
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

package_dependencies_el_model = ns.model(
    "SitePackageDependenciesElementModel",
    {
        "name": fields.String(description="the name of the dependent package"),
        "version": fields.String(description="the version of the dependent package"),
        "type": fields.String(description="dependency type"),
        "flag": fields.Integer(description="dependency flag"),
        "flag_decoded": fields.List(fields.String, description="decoded dependency flag"),
    }
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

depends_packages_el_model = ns.model(
    "SitePackagesElementModel",
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
        "changelog": fields.String(description="package last changelog message"),
    },
)
depends_packages_model = ns.model(
    "SitePackagesModel",
    {
        "request_args": fields.Raw(description="request arguments"),
        "length": fields.Integer(description="number of packages found"),
        "packages": fields.Nested(
            depends_packages_el_model,
            description="unpackaged directories information",
            as_list=True,
        ),
        "branches": fields.Nested(
            all_pkgsets_el_model,
            description="list of package sets with binary package count",
            as_list=True
        ),
    },
)