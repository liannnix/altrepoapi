from flask_restx import fields

from api.site.site import ns

package_info_changelog_el_model = ns.model(
    "SitePackageInfoChangelogElementModel",
    {
        "date": fields.String(description="changelog date"),
        "name": fields.String(description="changelog name"),
        "evr": fields.String(description="changelog EVR"),
        "message": fields.String(description="changelog message"),
    },
)
package_maintaners_el_model = ns.model(
    "SitePackageInfoMaintainersElementModel",
    {
        "name": fields.String(description="maintainer name"),
        "email": fields.String(description="maintainer email"),
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
package_info_tasks_el_model = ns.model(
    "SitePackageTasksElementModel",
    {
        "type": fields.String(description="task type"),
        "id": fields.String(description="task id"),
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
        "buildtime": fields.Integer(description="package build time"),
        "task": fields.Integer(description="package build task"),
        "gear": fields.String(description="package task gear type"),
        "license": fields.String(description="package license"),
        "category": fields.String(description="package group"),
        "url": fields.String(description="package url"),
        "summary": fields.String(description="package summary"),
        "description": fields.String(description="package description"),
        "packager": fields.String(description="package packager name"),
        "packager_email": fields.String(description="package packager email"),
        "packages": fields.List(fields.String, description="bunary packages"),
        "acl": fields.List(fields.String, description="bunary packages"),
        "tasks": fields.Nested(
            package_info_tasks_el_model, as_list=True, description="package tasks"
        ),
        "changelog": fields.Nested(
            package_info_changelog_el_model,
            as_list=True,
            description="package changelog",
        ),
        "maintainers": fields.Nested(
            package_maintaners_el_model,
            as_list=True,
            description="all package maintainers",
        ),
        "versions": fields.Nested(
            package_versions_el_model, as_list=True, description="all package versions"
        ),
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

pkgset_pkghash_model = ns.model(
    "SitePackagesetPackageHashModel",
    {
        "request_args": fields.Raw(description="request arguments"),
        "pkghash": fields.String(description="package hash UInt64 as string"),
        "version": fields.String(description="package version"),
        "release": fields.String(description="package release"),
    },
)


task_by_name_pkg_model = ns.model(
    "SiteTaskByNamePackageModel",
    {
        "type": fields.String(description="subtask type [gear|srpm|delete|search]"),
        "name": fields.String(description="package name"),
        "link": fields.String(description="package git link"),
    },
)
task_by_name_task_model = ns.model(
    "SiteTaskByNameTaskModel",
    {
        "id": fields.Integer(description="task id"),
        "state": fields.String(description="task state"),
        "branch": fields.String(description="task branch"),
        "owner": fields.String(description="task owner nickname"),
        "changed": fields.String(description="task last changed (ISO 8601 format)"),
        "packages": fields.Nested(
            task_by_name_pkg_model, description="task packages", as_list=True
        ),
    },
)
task_by_name_model = ns.model(
    "SiteTaskByNameModel",
    {
        "request_args": fields.Raw(description="request arguments"),
        "length": fields.Integer(description="number of tasks found"),
        "tasks": fields.Nested(
            task_by_name_task_model, description="tasks list", as_list=True
        ),
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

all_maintainers_el_model = ns.model(
    "AllMaintainersElementModel",
    {
        "pkg_packager": fields.String(description="Name maintainers"),
        "pkg_packager_email": fields.String(description="Email maintainers"),
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

maintainer_info_el_model = ns.model(
    "MaintainerInfoElementModel",
    {
        "maintainer_name": fields.Raw(description="Maintainer nickname"),
        "maintainer_email": fields.Raw(description="Maintainer email"),
        "last_buildtime": fields.String(description="Last buildtime"),
        "count_source_pkg": fields.Integer(description="Number of source packages"),
        "count_binary_pkg": fields.Integer(description="Number of binary packages"),
    },
)
maintainer_info_model = ns.model(
    "MaintainerInfoModel",
    {
        "request_args": fields.Raw(description="request arguments"),
        "information": fields.Nested(
            maintainer_info_el_model, description="maintainers info"
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

last_packages_el_model = ns.model(
    "SiteLastPackagesElementModel",
    {
        "subtask_id": fields.Integer(description="subtask id"),
        "subtask_userid": fields.String(description="subtask created by"),
        "subtask_type": fields.String(
            description="subtask type [build|rebuild|delete]"
        ),
        "hash": fields.String(
            attribute="pkg_hash", description="package hash UInt64 as string"
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
            attribute="pkg_buildtime", description="package buildtime"
        ),
        "changelog_date": fields.String(
            description="package last changelog message date"
        ),
        "changelog_text": fields.String(description="package last changelog message"),
    },
)
last_packages_pkg_model = ns.model(
    "SiteLastPackagesPackageModel",
    {
        "task_id": fields.Integer(description="task id"),
        "task_owner": fields.String(description="task owner"),
        "task_changed": fields.String(description="task completed at"),
        "task_message": fields.String(description="task message"),
        "packages": fields.Nested(
            last_packages_el_model,
            description="task subtasks packages information",
            as_list=True,
        ),
    },
)
last_packages_model = ns.model(
    "SiteLastPackagesModel",
    {
        "request_args": fields.Raw(description="request arguments"),
        "length": fields.Integer(description="number of packages found"),
        "tasks": fields.Nested(
            last_packages_pkg_model,
            description="last tasks packages information",
            as_list=True,
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
        "subtask_owner": fields.String(attribute="subtask_userid", description="subtask created by"),
        "task_changed": fields.String(description="task completed at"),
    }
)
