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

from flask import g, request
from flask_restx import Resource

from altrepo_api.utils import get_logger, url_logging
from altrepo_api.api.auth.decorators import auth_required
from altrepo_api.api.base import (
    run_worker,
    GET_RESPONSES_404,
    GET_RESPONSES_400_404,
    POST_RESPONSE_400_404,
)

from .namespace import get_namespace
from .endpoints.repocop import Repocop
from .endpoints.package_info import PackageInfo
from .endpoints.find_packageset import FindPackageset
from .endpoints.unpackaged_dirs import UnpackagedDirs
from .endpoints.package_by_file import PackageByFileName, PackageByFileMD5
from .endpoints.pkg_build_dependency import PackageBuildDependency
from .endpoints.misconflict_packages import PackageMisconflictPackages
from .endpoints.build_dependency_set import PackageBuildDependencySet
from .endpoints.specfile import SpecfileByPackageName, SpecfileByPackageHash
from .endpoints.package_files import PackageFiles
from .parsers import (
    package_info_args,
    pkg_build_dep_args,
    misconflict_pkg_args,
    pkg_repocop_args,
    pkg_find_pkgset_args,
    pkg_by_file_name_args,
    pkg_by_file_md5_args,
    unpackaged_dirs_args,
    build_dep_set_args,
    specfile_args,
)
from .serializers import (
    package_info_model,
    pkg_build_dep_model,
    misconflict_pkgs_model,
    pkg_find_pkgset_model,
    pkg_by_file_name_model,
    unpackaged_dirs_args_model,
    build_dep_set_model,
    repocop_json_list_model,
    repocop_json_get_list_model,
    specfile_model,
    package_files_model,
)

ns = get_namespace()

logger = get_logger(__name__)


@ns.route(
    "/package_info",
    doc={
        "description": "Get information for package by parameters from last packages",
        "responses": GET_RESPONSES_400_404,
    },
)
class routePackageInfo(Resource):
    @ns.expect(package_info_args)
    @ns.marshal_with(package_info_model)
    def get(self):
        url_logging(logger, g.url)
        args = package_info_args.parse_args(strict=True)
        w = PackageInfo(g.connection, **args)
        return run_worker(worker=w, args=args)


@ns.route(
    "/what_depends_src",
    doc={
        "description": "Get packages build dependencies by set of parameters",
        "responses": GET_RESPONSES_400_404,
    },
)
class routePackageBuildDependency(Resource):
    @ns.expect(pkg_build_dep_args)
    @ns.marshal_with(pkg_build_dep_model)
    def get(self):
        url_logging(logger, g.url)
        args = pkg_build_dep_args.parse_args(strict=True)
        w = PackageBuildDependency(g.connection, **args)
        return run_worker(worker=w, args=args)  # type: ignore


@ns.route(
    "/misconflict",
    doc={
        "description": (
            "Get packages with conflicting files in packages "
            "that don't have a conflict in dependencies"
        ),
        "responses": GET_RESPONSES_400_404,
    },
)
class routePackageMisconflictPackages(Resource):
    @ns.expect(misconflict_pkg_args)
    @ns.marshal_with(misconflict_pkgs_model)
    def get(self):
        url_logging(logger, g.url)
        args = misconflict_pkg_args.parse_args(strict=True)
        w = PackageMisconflictPackages(g.connection, **args)
        return run_worker(worker=w, args=args)  # type: ignore


@ns.route(
    "/find_packageset",
    doc={
        "description": (
            "Get information about packages from package sets "
            "by given source packages list"
        ),
        "responses": GET_RESPONSES_400_404,
    },
)
class routeFindPackageset(Resource):
    @ns.expect(pkg_find_pkgset_args)
    @ns.marshal_with(pkg_find_pkgset_model)
    def get(self):
        url_logging(logger, g.url)
        args = pkg_find_pkgset_args.parse_args(strict=True)
        w = FindPackageset(g.connection, **args)
        return run_worker(worker=w, args=args)


@ns.route(
    "/package_by_file_name",
    doc={
        "description": (
            "Get information about packages from  last package sets "
            "by given file name and package set name."
            "\nFile name wildcars '*' is allowed."
        ),
        "responses": GET_RESPONSES_400_404,
    },
)
class routePackageByFileName(Resource):
    @ns.expect(pkg_by_file_name_args)
    @ns.marshal_with(pkg_by_file_name_model)
    def get(self):
        url_logging(logger, g.url)
        args = pkg_by_file_name_args.parse_args(strict=True)
        w = PackageByFileName(g.connection, **args)
        return run_worker(worker=w, args=args)


@ns.route(
    "/package_by_file_md5",
    doc={
        "description": (
            "Get information about packages from  last package sets "
            "by given file MD5 checksum and package set name"
        ),
        "responses": GET_RESPONSES_400_404,
    },
)
class routePackageByFileMD5(Resource):
    @ns.expect(pkg_by_file_md5_args)
    @ns.marshal_with(pkg_by_file_name_model)
    def get(self):
        url_logging(logger, g.url)
        args = pkg_by_file_md5_args.parse_args(strict=True)
        w = PackageByFileMD5(g.connection, **args)
        return run_worker(worker=w, args=args)


@ns.route(
    "/unpackaged_dirs",
    doc={
        "description": (
            "Get information about unpackaged directories " "by maintainer nickname"
        ),
        "responses": GET_RESPONSES_400_404,
    },
)
class routeUnpackagedDirs(Resource):
    @ns.expect(unpackaged_dirs_args)
    @ns.marshal_with(unpackaged_dirs_args_model)
    def get(self):
        url_logging(logger, g.url)
        args = unpackaged_dirs_args.parse_args(strict=True)
        w = UnpackagedDirs(g.connection, **args)
        return run_worker(worker=w, args=args)


@ns.route(
    "/build_dependency_set",
    doc={
        "description": (
            "Get list of packages required for build by given "
            "packages list recursively"
        ),
        "responses": GET_RESPONSES_400_404,
    },
)
class routePackageBuildDependencySet(Resource):
    @ns.expect(build_dep_set_args)
    @ns.marshal_with(build_dep_set_model)
    def get(self):
        url_logging(logger, g.url)
        args = build_dep_set_args.parse_args(strict=True)
        w = PackageBuildDependencySet(g.connection, **args)
        return run_worker(worker=w, args=args)  # type: ignore


@ns.route("/repocop")
class routePackageRepocop(Resource):
    @ns.doc(
        description="Load repocop data into database",
        responses=POST_RESPONSE_400_404,
    )
    @ns.expect(repocop_json_list_model)
    @ns.doc(security="BasicAuth")
    @auth_required
    def post(self):
        url_logging(logger, g.url)
        args = {}
        w = Repocop(g.connection, json_data=request.json)
        return run_worker(
            worker=w,
            run_method=w.post,
            check_method=w.check_params_post,
            args=args,
            ok_code=201,
        )

    @ns.doc(
        description="Get repocop data by name, version and release",
        responses=GET_RESPONSES_400_404,
    )
    @ns.expect(pkg_repocop_args)
    @ns.marshal_with(repocop_json_get_list_model)
    def get(self):
        url_logging(logger, g.url)
        args = pkg_repocop_args.parse_args(strict=True)
        w = Repocop(g.connection, **args)
        return run_worker(
            worker=w, run_method=w.get, check_method=w.check_params_get, args=args
        )


@ns.route(
    "/specfile_by_hash/<int:pkghash>",
    doc={
        "params": {"pkghash": "package hash"},
        "description": "Get spec file by source package hash",
        "responses": GET_RESPONSES_404,
    },
)
class routeSpecfileByPackageHash(Resource):
    pass

    @ns.expect()
    @ns.marshal_with(specfile_model)
    def get(self, pkghash):
        url_logging(logger, g.url)
        args = {}
        w = SpecfileByPackageHash(g.connection, pkghash, **args)
        return run_worker(worker=w, args=args)


@ns.route(
    "/specfile_by_name",
    doc={
        "description": ("Get spec file by source package name and branch"),
        "responses": GET_RESPONSES_404,
    },
)
class routeSpecfileByPackageName(Resource):
    @ns.expect(specfile_args)
    @ns.marshal_with(specfile_model)
    def get(self):
        url_logging(logger, g.url)
        args = specfile_args.parse_args(strict=True)
        w = SpecfileByPackageName(g.connection, **args)
        return run_worker(worker=w, args=args)


@ns.route(
    "/package_files/<int:pkghash>",
    doc={
        "description": "Get package files by hash",
        "responses": GET_RESPONSES_404,
    },
)
class routeBinPackageFiles(Resource):
    # @ns.expect()
    @ns.marshal_with(package_files_model)
    def get(self, pkghash):
        url_logging(logger, g.url)
        args = {}
        w = PackageFiles(g.connection, pkghash)
        return run_worker(worker=w, args=args)
