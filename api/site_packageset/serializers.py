from flask_restx import fields

from .namespace import get_namespace

ns = get_namespace()


package_versions_el_model = ns.model(
    "SitePackageVersionsElementModel",
    {
        "branch": fields.String(description="package set name"),
        "version": fields.String(description="package version"),
        "release": fields.String(description="package release"),
        "pkghash": fields.String(description="package hash UInt64 as string"),
    },
)


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
        "subcategories": fields.List(fields.String, description="list of subcategories"),
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


fing_pkgs_by_name_pkg_model = ns.model(
    "SiteFingPackagesPackageModel",
    {
        "name": fields.String(description="package name"),
        "buildtime": fields.Integer(description="package build time"),
        "url": fields.String(description="package url"),
        "summary": fields.String(description="package summary"),
        "category": fields.String(description="package category"),
        "versions": fields.Nested(
            package_versions_el_model, as_list=True, description="all package versions"
        ),
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
        "branches": fields.List(fields.String, description="list of package branches")
    }
)
fast_pkgs_search_model = ns.model(
    "SiteFastPackagesSearchModel",
    {
        "request_args": fields.Raw(description="request arguments"),
        "length": fields.Integer(description="number of packages found"),
        "packages": fields.Nested(
            fast_pkgs_search_el_model,
            description="list of found packages",
            as_list=True,)
    }
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
        "hash": fields.String(
            description="package hash UInt64 as string"
        ),
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
    }
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
    }
)
