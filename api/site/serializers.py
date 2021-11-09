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


all_pkgsets_el_model = ns.model(
    "SiteAllPackagasetsElementModel",
    {
        "branch": fields.String(description="package set name"),
        "count": fields.Integer(description="number of source packages"),
    },
)
all_pkgsets_model = ns.model(
    "SiteAllPackagasetsModel",
    {
        "length": fields.Integer(description="number of package sets found"),
        "branches": fields.Nested(
            all_pkgsets_el_model,
            description="list of package sets with source package count",
            as_list=True,
        ),
    },
)


all_archs_el_model = ns.model(
    "SiteAllArchsElementModel",
    {
        "arch": fields.String(description="binary package arch"),
        "count": fields.Integer(description="number of source packages"),
    },
)
all_archs_model = ns.model(
    "SiteAllArchsModel",
    {
        "length": fields.Integer(
            description="number of binary package archs and source packages count"
        ),
        "archs": fields.Nested(
            all_archs_el_model, description="binary package archs", as_list=True
        ),
    },
)


pkgset_category_model = ns.model(
    "SitePackagesetCategoryElementModel",
    {
        "category": fields.String(description="package category"),
        "count": fields.Integer(description="number of packages in category"),
    },
)
pkgset_categories_model = ns.model(
    "SitePackagesetCategoriesModel",
    {
        "request_args": fields.Raw(description="request arguments"),
        "length": fields.Integer(description="number of categories in list"),
        "categories": fields.Nested(
            pkgset_category_model, description="found categories", as_list=True
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


all_pkgsets_summary_counts_model = ns.model(
    "SiteAllPackagesetsSummaryCountsModel",
    {
        "arch": fields.String(description="binary packages arch"),
        "count": fields.Integer(description="source packages count"),
    },
)
all_pkgsets_summary_branches_model = ns.model(
    "SiteAllPackagesetsSummaryBranchesModel",
    {
        "branch": fields.String(description="package set name"),
        "packages_count": fields.Nested(
            all_pkgsets_summary_counts_model,
            description="list of source packages count by binary packages archs",
            as_list=True,
        ),
    },
)
all_pkgsets_summary_model = ns.model(
    "SiteAllPackagesetsSummaryModel",
    {
        "length": fields.Integer(description="number of packages found"),
        "branches": fields.Nested(
            all_pkgsets_summary_branches_model,
            description="list of branches with source packages count",
            as_list=True,
        ),
    },
)


pkgsets_status_el_model = ns.model(
    "SitePackagesetStatusElementModel",
    {
        "branch": fields.String(description="package set name"),
        "start_date": fields.DateTime(description="support start date"),
        "end_date": fields.DateTime(description="support end date"),
        "show": fields.Integer(description="0 - hide branch, 1 - show branch"),
        "description_ru": fields.String(description="html description in Russian"),
        "description_en": fields.String(description="html description in English"),
    }
)
pkgsets_summary_status_model = ns.model(
    "SitePackagesetsSummaryStatusModel",
    {
        "length": fields.Integer(description="number of packages found"),
        "branches": fields.Nested(
            all_pkgsets_summary_branches_model,
            description="list of branches with source packages count",
            as_list=True,
        ),
        "status": fields.Nested(
            pkgsets_status_el_model,
            description="list of branches status",
            as_list=True,
        ),
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
