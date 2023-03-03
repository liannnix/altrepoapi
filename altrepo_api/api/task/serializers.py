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

task_repo_package_model = ns.model(
    "TaskRepoPackageModel",
    {
        "name": fields.String(description="package name"),
        "version": fields.String(description="package version"),
        "release": fields.String(description="package release"),
        "filename": fields.String(description="package file name"),
    },
)

task_repo_info_model = ns.model(
    "TaskRepoInfoModel",
    {
        "name": fields.String(description="package set name"),
        "date": fields.String(description="package set upload date in ISO8601 format"),
        "tag": fields.String(description="package set upload tag"),
    },
)

task_repo_archs_model = ns.model(
    "TaskRepoArchsModel",
    {
        "arch": fields.String(description="architecture"),
        "packages": fields.Nested(
            task_repo_package_model, description="packages list", as_list=True
        ),
    },
)

task_repo_model = ns.model(
    "TaskRepoModel",
    {
        "task_id": fields.Integer(description="task id"),
        "base_repository": fields.Nested(
            task_repo_info_model, description="last uploaded package set used as base"
        ),
        "task_diff_list": fields.List(
            fields.Integer, description="list of tasks applied to base package set"
        ),
        "archs": fields.Nested(
            task_repo_archs_model,
            description="list of packages by architectures",
            as_list=True,
        ),
    },
)

task_diff_dependencies_model = ns.model(
    "TaskDiffDependenciesModel",
    {
        "type": fields.String,
        "del": fields.List(fields.String),
        "add": fields.List(fields.String),
    },
)

task_diff_packages_model = ns.model(
    "TaskDiffPackagesModel",
    {
        "package": fields.String,
        "del": fields.List(fields.String),
        "add": fields.List(fields.String),
        "dependencies": fields.Nested(task_diff_dependencies_model, as_list=True),
    },
)

task_diff_archs_model = ns.model(
    "TaskDiffArchsModel",
    {
        "arch": fields.String,
        "packages": fields.Nested(task_diff_packages_model, as_list=True),
    },
)

task_diff_model = ns.model(
    "TaskDiffModel",
    {
        "task_id": fields.Integer(description="task id"),
        "task_have_plan": fields.Boolean(
            description="task have package hashses add/delete plan"
        ),
        "task_diff": fields.Nested(
            task_diff_archs_model, as_list=True, description="task diff"
        ),
    },
)

task_info_package_model = ns.model(
    "TaskInfoPackageModel",
    {
        "name": fields.String(description="package name"),
        "version": fields.String(description="package version"),
        "release": fields.String(description="package release"),
        "filename": fields.String(description="package file name"),
    },
)

task_info_approvals_model = ns.model(
    "TaskInfoApprovalsModel",
    {
        "date": fields.String(description="approval date"),
        "type": fields.String(description="approval type"),
        "name": fields.String(description="approver name"),
        "message": fields.String(description="approval message"),
    },
)

task_info_archs_model = ns.model(
    "TaskInfoArchsModel",
    {
        "last_changed": fields.String(description="iteration state last changed"),
        "arch": fields.String(description="iteration arch"),
        "status": fields.String(description="iteration state"),
    },
)

task_info_subtask_model = ns.model(
    "TaskInfoSubtaskModel",
    {
        "subtask_id": fields.Integer(description="subtask id"),
        "last_changed": fields.String(description="subtask state last changed"),
        "userid": fields.String(description="subtask creator"),
        "type": fields.String(description="subtask type"),
        "sid": fields.String(description="subtask sid"),
        "dir": fields.String(description="subtask dir"),
        "package": fields.String(description="subtask package"),
        "tag_author": fields.String(description="gear tag author"),
        "tag_name": fields.String(description="gear tag name"),
        "tag_id": fields.String(description="gear tag id"),
        "srpm": fields.String(description="source package"),
        "srpm_name": fields.String(description="source package name"),
        "srpm_evr": fields.String(description="source package EVR"),
        "pkg_from": fields.String(description="package copy from"),
        "source_package": fields.Nested(task_info_package_model),
        "approvals": fields.Nested(
            task_info_approvals_model, as_list=True, description="subtask approvals"
        ),
        "archs": fields.Nested(
            task_info_archs_model, as_list=True, description="subtask archs"
        ),
    },
)

task_info_plan_model = ns.model(
    "TaskInfoPlanModel",
    {
        "src": fields.Nested(
            task_info_package_model, as_list=True, description="source packages"
        ),
        "bin": fields.Nested(
            task_info_package_model, as_list=True, description="binary packages"
        ),
    },
)

task_info_plan2_model = ns.model(
    "TaskInfoPlan2Model",
    {
        "add": fields.Nested(task_info_plan_model, description="added packages"),
        "del": fields.Nested(task_info_plan_model, description="deleted packages"),
    },
)

task_info_model = ns.model(
    "TaskInfoModel",
    {
        "id": fields.Integer(description="task id"),
        "prev": fields.Integer(description="previous task id"),
        "try": fields.Integer(description="task try"),
        "iter": fields.Integer(description="task iteration"),
        "rebuilds": fields.List(fields.String(), description="all task rebuilds"),
        "state": fields.String(description="task state"),
        "branch": fields.String(description="task branch"),
        "user": fields.String(description="task owner"),
        "runby": fields.String(description="task ran by"),
        "testonly": fields.Integer(description="testonly flag"),
        "failearly": fields.Integer(description="failearly flag"),
        "shared": fields.Integer(description="shared flag"),
        "depends": fields.List(fields.Integer(), description="task depends on"),
        "message": fields.String(description="task message"),
        "version": fields.String(description="task version"),
        "last_changed": fields.String(description="task state last changed"),
        "subtasks": fields.Nested(
            task_info_subtask_model, as_list=True, description="task subtasks"
        ),
        "plan": fields.Nested(
            task_info_plan2_model, description="task packages add/delete"
        ),
    },
)

task_build_dep_el_model = ns.model(
    "TaskBuildDependencyElementModel",
    {
        "depth": fields.Integer(description="package dependenyc depth"),
        "name": fields.String(description="package name"),
        "version": fields.String(description="package version"),
        "release": fields.String(description="package release"),
        "epoch": fields.Integer(description="package epoch"),
        "serial": fields.Integer(attribute="serial_", description="package serial"),
        "sourcerpm": fields.String(description="source package file"),
        "branch": fields.String(description="package set name"),
        "buildtime": fields.String(description="package build time"),
        "archs": fields.List(fields.String, description="package archs"),
        "cycle": fields.List(fields.String, description="package cycle dependencies"),
        "requires": fields.List(fields.String, description="package requirements"),
        "acl": fields.List(fields.String, description="package ACL list"),
    },
)

task_build_dep_model = package_info_model = ns.model(
    "TaskBuildDependencyModel",
    {
        "id": fields.Integer(description="task id"),
        "request_args": fields.Raw(description="request arguments"),
        "length": fields.Integer(description="number of packages found"),
        "dependencies": fields.Nested(
            task_build_dep_el_model,
            description="build dependency results",
            as_list=True,
        ),
    },
)

misconflict_pkg_model = ns.model(
    "TaskMisconflictPackageModel",
    {
        "input_package": fields.String(description="package name"),
        "conflict_package": fields.String(description="package name"),
        "version": fields.String(description="package version"),
        "release": fields.String(description="package release"),
        "epoch": fields.Integer(description="package epoch"),
        "archs": fields.List(fields.String, description="package archs"),
        "files_with_conflict": fields.List(fields.String, description="conflict files"),
    },
)

misconflict_pkgs_model = ns.model(
    "TaskMisconflictPackagesModel",
    {
        "id": fields.Integer(description="task id"),
        "request_args": fields.Raw(description="request arguments"),
        "length": fields.Integer(description="number of packages found"),
        "conflicts": fields.Nested(
            misconflict_pkg_model, description="conflicts", as_list=True
        ),
    },
)

task_find_pkgset_el_model = ns.model(
    "TaskFindPackagesetElementModel",
    {
        "branch": fields.String(description="package set name"),
        "pkgset_datetime": fields.String(description="package set date"),
        "sourcepkgname": fields.String(description="source package name"),
        "packages": fields.List(fields.String, description="binary packages list"),
        "version": fields.String(description="package version"),
        "release": fields.String(description="package release"),
        "disttag": fields.String(description="package disttag"),
        "packager_email": fields.String(description="package packager email"),
        "buildtime": fields.String(description="package build time"),
        "archs": fields.List(fields.String, description="binary packages archs"),
    },
)

task_find_pkgset_model = ns.model(
    "TaskFindPackagesetModel",
    {
        "id": fields.Integer(description="task id"),
        "request_args": fields.Raw(description="request arguments"),
        "task_packages": fields.List(fields.String, description="request arguments"),
        "length": fields.Integer(description="number of packages found"),
        "packages": fields.Nested(
            task_find_pkgset_el_model,
            description="package set packages information",
            as_list=True,
        ),
    },
)

build_dep_set_pkg_model = ns.model(
    "BuildDependencySetPackageModel",
    {
        "name": fields.String(description="package name"),
        "version": fields.String(description="package version"),
        "release": fields.String(description="package release"),
        "epoch": fields.Integer(description="package epoch"),
        "archs": fields.List(fields.String, description="binary packages archs"),
    },
)
build_dep_set_pkgs_model = ns.model(
    "BuildDependencySetPackagesModel",
    {
        "package": fields.String(description="source package name"),
        "length": fields.Integer(description="number of dependency packages found"),
        "depends": fields.Nested(
            build_dep_set_pkg_model,
            description="build requirements packages information",
            as_list=True,
        ),
    },
)
build_dep_set_amb_deps_pkg_model = ns.model(
    "BuildDependencySetAmbiguousProvidesPackageModel",
    {
        "name": fields.String(description="package name"),
        "used": fields.Boolean(description="package used as provide dependency"),
    },
)
build_dep_set_amb_deps_dep_model = ns.model(
    "BuildDependencySetAmbiguousProvidesElementModel",
    {
        "requires": fields.String(description="package require dependency name"),
        "provides_count": fields.Integer(
            description="ambiguous provides packaages count"
        ),
        "provides": fields.Nested(
            build_dep_set_amb_deps_pkg_model,
            description="list of packages that provides required dependency",
            as_list=True,
        ),
    },
)
build_dep_set_amb_deps_model = ns.model(
    "BuildDependencySetAmbiguousProvidesModel",
    {
        "package": fields.String(description="package name"),
        "ambiguous_provides": fields.Nested(
            build_dep_set_amb_deps_dep_model,
            description="list of found and resolved ambiguous provides",
            as_list=True,
        ),
    },
)
build_dep_set_model = ns.model(
    "BuildDependencySetModel",
    {
        "id": fields.Integer(description="task id"),
        "request_args": fields.Raw(description="request arguments"),
        "length": fields.Integer(description="number of packages found"),
        "packages": fields.Nested(
            build_dep_set_pkgs_model,
            description="build requirements packages information",
            as_list=True,
        ),
        "ambiguous_dependencies": fields.Nested(
            build_dep_set_amb_deps_model,
            description="list of found and resolved ambiguous dependencies",
            as_list=True,
        ),
    },
)

task_history_el_model = ns.model(
    "TaskHistoryElementModel",
    {
        "task_id": fields.Integer(description="task id"),
        "task_commited": fields.String(
            description="task commited date in ISO8601 format"
        ),
        "branch_commited": fields.String(
            description="branch commited date in ISO8601 format"
        ),
    },
)
task_history_model = ns.model(
    "TaskHistoryModel",
    {
        "request_args": fields.Raw(description="request arguments"),
        "length": fields.Integer(description="number of packages found"),
        "tasks": fields.Nested(
            task_history_el_model,
            description="build requirements packages information",
            as_list=True,
        ),
    },
)

find_images_by_task_image_el_model = ns.model(
    "FindImagesByTaskImageElementModel",
    {
        "filename": fields.String(description="image filename"),
        "edition": fields.String(description="image edition"),
        "tag": fields.String(description="image tag"),
        "buildtime": fields.DateTime(description="image built date in ISO8601 format"),
        "binpkg_name": fields.String(description="image's binary package name"),
        "binpkg_version": fields.String(description="image's binary package version"),
        "binpkg_release": fields.String(description="image's binary package release"),
        "binpkg_arch": fields.String(description="image's binary package architecture"),
        "binpkg_hash": fields.String(description="image's binary package hash")
    }
)
find_images_by_task_subtask_el_model = ns.model(
    "FindImagesByTaskSubtaskElementModel",
    {
        "id": fields.Integer(description="subtask id"),
        "type": fields.String(description="subtask type"),
        "srpm_name": fields.String(description="subtask srpm name"),
        "srpm_hash": fields.String(description="subtask srpm hash"),
        "pkg_version": fields.String(description="subtask's source package version"),
        "pkg_release": fields.String(description="subtask's source package release"),
        "images": fields.Nested(
            find_images_by_task_image_el_model,
            description="affected images (by binary packages)",
            as_list=True
        ),
    }
)
find_image_by_task_iteration_el_model = ns.model(
    "FindImagesByTaskIterationElementModel",
    {
        "task_try": fields.Integer(description="task try"),
        "task_iter": fields.Integer(description="task iter")
    }
)
find_images_by_task_model = ns.model(
    "FindImagesByTaskModel",
    {
        "task_id": fields.Integer(description="task id"),
        "task_state": fields.String(description="task state"),
        "task_testonly": fields.Integer(description="task is test-only"),
        "task_repo": fields.String(description="task repo"),
        "task_owner": fields.String(description="task owner"),
        "task_try": fields.Integer(description="task try"),
        "task_iter": fields.Integer(description="task iter"),
        "task_message": fields.String(description="task message"),
        "task_changed": fields.DateTime(descrption="task changed date in ISO8601 format"),
        "dependencies": fields.List(fields.Integer, description="task dependencies"),
        "subtasks": fields.Nested(
            find_images_by_task_subtask_el_model,
            description="subtasks",
            as_list=True
        ),
        "iterations": fields.Nested(
            find_image_by_task_iteration_el_model,
            descriptions="iterations",
            as_list=True
        )
    }
)
