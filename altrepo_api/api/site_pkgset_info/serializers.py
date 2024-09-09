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
tasks_history_task_model = ns.model(
    "TasksHistoryTaskModel",
    {
        "id": fields.Integer(description="task ID"),
        "prev": fields.Integer(description="previous task ID"),
        "branch": fields.String(description="task branch name"),
        "date": fields.String(description="task build time"),
    },
)
tasks_history_branch_commit_model = ns.model(
    "TasksHistoryBranchCommitModel",
    {
        "name": fields.String(description="branch name"),
        "date": fields.String(description="branch commit date"),
        "task": fields.Integer(description="task ID"),
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
        "has_images": fields.Integer(
            description="0 - branch has no active images, 1 - branch has active images"
        ),
    },
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
tasks_history_model = ns.model(
    "SiteTasksHistoryModel",
    {
        "branches": fields.List(fields.String, description="list of active branches"),
        "tasks": fields.Nested(
            tasks_history_task_model, description="branches tasks list", as_list=True
        ),
        "branch_commits": fields.Nested(
            tasks_history_branch_commit_model,
            description="branches commits list",
            as_list=True,
        ),
    },
)
