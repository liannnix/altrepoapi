# ALTRepo API
# Copyright (C) 2021-2026  BaseALT Ltd

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

pkgset_compare_pkg_model = ns.model(
    "PackagesetComparePackageModel",
    {
        "name": fields.String(description="package name"),
        "version": fields.String(description="package version"),
        "release": fields.String(description="package release"),
    },
)
pkgset_compare_el_model = ns.model(
    "PackagesetCompareElementModel",
    {
        "pkgset1": fields.String(description="packageset #1 name"),
        "pkgset2": fields.String(description="packageset #2 name"),
        "package1": fields.Nested(
            pkgset_compare_pkg_model, description="package from packageset #1"
        ),
        "package2": fields.Nested(
            pkgset_compare_pkg_model, description="package from packageset #2"
        ),
    },
)
pkgset_compare_model = ns.model(
    "PackagesetCompareModel",
    {
        "request_args": fields.Raw(description="request arguments"),
        "length": fields.Integer(description="number of packages found"),
        "packages": fields.Nested(
            pkgset_compare_el_model,
            description="packages information",
            as_list=True,
        ),
    },
)

pkgset_packages_el_model = ns.model(
    "PackagesetPackagesElementModel",
    {
        "hash": fields.String(description="package hash UInt64 as string"),
        "name": fields.String(description="package name"),
        "version": fields.String(description="package version"),
        "release": fields.String(description="package release"),
        "summary": fields.String(description="package summary"),
        "url": fields.String(description="package url"),
        "license": fields.String(description="package license"),
        "category": fields.String(description="package category"),
        "maintainers": fields.List(fields.String, description="package maintainers"),
        "acl_list": fields.List(fields.String, description="package ACL list"),
        "archs": fields.List(fields.String, description="package archs"),
    },
)
pkgset_packages_model = ns.model(
    "PackagesetPackagesModel",
    {
        "request_args": fields.Raw(description="request arguments"),
        "length": fields.Integer(description="number of packages found"),
        "packages": fields.Nested(
            pkgset_packages_el_model,
            description="packages information",
            as_list=True,
        ),
        "done_tasks": fields.List(
            fields.Integer,
            description="list of DONE task IDs applied to repository state",
        ),
    },
)

pkgset_status_post_el_model = ns.model(
    "PackageSetStatusPostElementModel",
    {
        "pkgset_name": fields.String(description="package set name", required=True),
        "rs_pkgset_name_bugzilla": fields.String(
            description="package set name for bugzilla", required=True
        ),
        "rs_start_date": fields.DateTime(
            description="support start date", required=True
        ),
        "rs_end_date": fields.DateTime(description="support end date", required=True),
        "rs_show": fields.Integer(
            description="0 - hide branch, 1 - show branch", required=True
        ),
        "rs_description_ru": fields.String(
            description="html description in Russian in Base64 format", required=True
        ),
        "rs_description_en": fields.String(
            description="html description in English in Base64 format", required=True
        ),
        "rs_mailing_list": fields.String(
            description="link to mailing list", required=True
        ),
        "rs_mirrors_json": fields.List(
            fields.Raw,
            description="packageset mirror's auxilary info as JSON substructure",
        ),
    },
)
pkgset_status_post_model = ns.model(
    "PackageSetStatusPostModel",
    {
        "branches": fields.Nested(
            pkgset_status_post_el_model,
            description="package set info",
            as_list=True,
            required=True,
        )
    },
)

pkgset_status_get_el_model = ns.model(
    "PackageSetStatusGetElementModel",
    {
        "branch": fields.String(description="package set name"),
        "pkgset_name_bugzilla": fields.String(
            description="package set name for bugzilla"
        ),
        "start_date": fields.DateTime(description="support start date"),
        "end_date": fields.DateTime(description="support end date"),
        "show": fields.Integer(description="0 - hide branch, 1 - show branch"),
        "description_ru": fields.String(description="html description in Russian"),
        "description_en": fields.String(description="html description in English"),
        "url_mailing_list": fields.String(description="link to mailing list"),
        "mirrors_json": fields.Raw(
            description="packageset mirror's auxilary info as JSON substructure"
        ),
        "has_images": fields.Integer(
            description="0 - branch has no active images, 1 - branch has active images"
        ),
    },
)
pkgset_status_get_model = ns.model(
    "PackageSetStatusGetModel",
    {
        "branches": fields.Nested(
            pkgset_status_get_el_model, description="package set info", as_list=True
        )
    },
)

active_pkgsets_model = ns.model(
    "PackageSetActivePackageSetsModel",
    {
        "length": fields.Integer(description="number of active package sets found"),
        "packagesets": fields.List(
            fields.String, description="active package sets list"
        ),
    },
)

repository_statistics_package_counts_model = ns.model(
    "RepositoryStatisticsPackageCountsModel",
    {
        "arch": fields.String(description="packages arch"),
        "component": fields.String(description="component name"),
        "count": fields.Integer(description="packages count"),
        "size": fields.Integer(description="total packages files size in bytes"),
        "size_hr": fields.String(
            description="total packages files size human readable"
        ),
        "uuid": fields.String(description="repository component UUID"),
    },
)
repository_statistics_branches_model = ns.model(
    "RepositoryStatisticsBranchesModel",
    {
        "branch": fields.String(description="package set name"),
        "date_update": fields.DateTime(description="branch upload date"),
        "packages_count": fields.Nested(
            repository_statistics_package_counts_model,
            description="list of packages count by package archs",
            as_list=True,
        ),
    },
)
repository_statistics_model = ns.model(
    "RepositoryStatisticsModel",
    {
        "length": fields.Integer(description="number of packages found"),
        "branches": fields.Nested(
            repository_statistics_branches_model,
            description="list of branches with packages count",
            as_list=True,
        ),
    },
)

packages_by_uuid_el_model = ns.model(
    "PackagesByUuidElementModel",
    {
        "hash": fields.String(description="package hash UInt64 as string"),
        "name": fields.String(attribute="pkg_name", description="package name"),
        "version": fields.String(
            attribute="pkg_version", description="package version"
        ),
        "release": fields.String(
            attribute="pkg_release", description="package release"
        ),
        "arch": fields.String(attribute="pkg_arch", description="package architecture"),
        "sourcerpm": fields.String(description="source package file"),
        "summary": fields.String(
            attribute="pkg_summary", description="package summary"
        ),
        "buildtime": fields.Integer(
            attribute="pkg_buildtime", description="last binary package buildtime"
        ),
        "changelog_text": fields.String(description="package last changelog message"),
    },
)
packages_by_uuid_model = ns.model(
    "PackagesByUuidModel",
    {
        "request_args": fields.Raw(description="request arguments"),
        "length": fields.Integer(description="number of packages found"),
        "packages": fields.Nested(
            packages_by_uuid_el_model,
            description="packages list by packageset component UUID",
            as_list=True,
        ),
    },
)

maintainer_scores_batch_maintainer_model = ns.model(
    "MaintainerScoresBatchMaintainerModel",
    {
        "nick": fields.String(description="maintainer nickname"),
        "score": fields.Float(description="maintainer score (with bonuses)"),
        "base_score": fields.Float(description="base score (changelog + bugfixes)"),
        "updates": fields.Integer(description="number of upstream updates (alt1)"),
        "patches": fields.Integer(description="number of patches/fixes"),
        "nmu": fields.Integer(description="number of NMU uploads"),
        "bugfixes": fields.Integer(description="number of Bugzilla bugs fixed"),
        "in_acl": fields.Boolean(description="maintainer is in current ACL"),
        "last_activity": fields.String(description="last activity date"),
        "recent_commits": fields.Integer(description="commits in last 6 months"),
        "bonus_applied": fields.Boolean(description="recent maintainer bonus applied"),
    },
)
maintainer_scores_batch_el_model = ns.model(
    "MaintainerScoresBatchElementModel",
    {
        "package": fields.String(description="source package name"),
        "primary_maintainer": fields.String(
            description="primary maintainer nickname (highest score)"
        ),
        "status": fields.String(
            description="package status: active, low_activity, orphaned"
        ),
        "maintainers": fields.Nested(
            maintainer_scores_batch_maintainer_model,
            description="list of maintainers with scores",
            as_list=True,
        ),
    },
)
maintainer_scores_batch_model = ns.model(
    "MaintainerScoresBatchModel",
    {
        "request_args": fields.Raw(description="request arguments"),
        "branch": fields.String(description="branch name"),
        "length": fields.Integer(description="number of packages found"),
        "packages": fields.Nested(
            maintainer_scores_batch_el_model,
            description="list of packages with maintainer scores",
            as_list=True,
        ),
    },
)
