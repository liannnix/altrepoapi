# altrepodb API
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
from flask_restx import Resource, abort

from utils import get_logger, url_logging, response_error_parser
from api.auth.decorators import auth_required

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
        "responses": {
            400: "Request parameters validation error",
            404: "Package not found in database",
        },
    },
)
class routePackageInfo(Resource):
    @ns.expect(package_info_args)
    @ns.marshal_with(package_info_model)
    def get(self):
        args = package_info_args.parse_args(strict=True)
        url_logging(logger, g.url)
        wrk = PackageInfo(g.connection, **args)
        if not wrk.check_params():
            abort(
                400,
                message=f"Request parameters validation error",
                args=args,
                validation_message=wrk.validation_results,
            )
        result, code = wrk.get()
        if code != 200:
            abort(code, **response_error_parser(result))
        return result, code


@ns.route(
    "/what_depends_src",
    doc={
        "description": "Get packages build dependencies by set of parameters",
        "responses": {
            400: "Request parameters validation error",
            404: "Requested data not found in database",
        },
    },
)
class routePackageBuildDependency(Resource):
    @ns.expect(pkg_build_dep_args)
    @ns.marshal_with(pkg_build_dep_model)
    def get(self):
        args = pkg_build_dep_args.parse_args(strict=True)
        url_logging(logger, g.url)
        wrk = PackageBuildDependency(g.connection, **args)
        if not wrk.check_params():
            abort(
                400,
                message=f"Request parameters validation error",
                args=args,
                validation_message=wrk.validation_results,
            )
        result, code = wrk.get()
        if code != 200:
            abort(code, **response_error_parser(result))
        return result, code


@ns.route(
    "/misconflict",
    doc={
        "description": (
            "Get packages with conflicting files in packages "
            "that don't have a conflict in dependencies"
        ),
        "responses": {
            400: "Request parameters validation error",
            404: "Requested data not found in database",
        },
    },
)
class routePackageMisconflictPackages(Resource):
    @ns.expect(misconflict_pkg_args)
    @ns.marshal_with(misconflict_pkgs_model)
    def get(self):
        args = misconflict_pkg_args.parse_args(strict=True)
        url_logging(logger, g.url)
        wrk = PackageMisconflictPackages(g.connection, **args)
        if not wrk.check_params():
            abort(
                400,
                message=f"Request parameters validation error",
                args=args,
                validation_message=wrk.validation_results,
            )
        result, code = wrk.get()
        if code != 200:
            abort(code, **response_error_parser(result))
        return result, code


@ns.route(
    "/find_packageset",
    doc={
        "description": (
            "Get information about packages from package sets "
            "by given source packages list"
        ),
        "responses": {
            400: "Request parameters validation error",
            404: "Package not found in database",
        },
    },
)
class routeFindPackageset(Resource):
    @ns.expect(pkg_find_pkgset_args)
    @ns.marshal_with(pkg_find_pkgset_model)
    def get(self):
        args = pkg_find_pkgset_args.parse_args(strict=True)
        url_logging(logger, g.url)
        wrk = FindPackageset(g.connection, **args)
        if not wrk.check_params():
            abort(
                400,
                message=f"Request parameters validation error",
                args=args,
                validation_message=wrk.validation_results,
            )
        result, code = wrk.get()
        if code != 200:
            abort(code, **response_error_parser(result))
        return result, code


@ns.route(
    "/package_by_file_name",
    doc={
        "description": (
            "Get information about packages from  last package sets "
            "by given file name and package set name."
            "\nFile name wildcars '*' is allowed."
        ),
        "responses": {
            400: "Request parameters validation error",
            404: "Package not found in database",
        },
    },
)
class routePackageByFileName(Resource):
    @ns.expect(pkg_by_file_name_args)
    @ns.marshal_with(pkg_by_file_name_model)
    def get(self):
        args = pkg_by_file_name_args.parse_args(strict=True)
        url_logging(logger, g.url)
        wrk = PackageByFileName(g.connection, **args)
        if not wrk.check_params():
            abort(
                400,
                message=f"Request parameters validation error",
                args=args,
                validation_message=wrk.validation_results,
            )
        result, code = wrk.get()
        if code != 200:
            abort(code, **response_error_parser(result))
        return result, code


@ns.route(
    "/package_by_file_md5",
    doc={
        "description": (
            "Get information about packages from  last package sets "
            "by given file MD5 checksum and package set name"
        ),
        "responses": {
            400: "Request parameters validation error",
            404: "Package not found in database",
        },
    },
)
class routePackageByFileMD5(Resource):
    @ns.expect(pkg_by_file_md5_args)
    @ns.marshal_with(pkg_by_file_name_model)
    def get(self):
        args = pkg_by_file_md5_args.parse_args(strict=True)
        url_logging(logger, g.url)
        wrk = PackageByFileMD5(g.connection, **args)
        if not wrk.check_params():
            abort(
                400,
                message=f"Request parameters validation error",
                args=args,
                validation_message=wrk.validation_results,
            )
        result, code = wrk.get()
        if code != 200:
            abort(code, **response_error_parser(result))
        return result, code


@ns.route(
    "/unpackaged_dirs",
    doc={
        "description": (
            "Get information about unpackaged directories " "by maintainer nickname"
        ),
        "responses": {
            400: "Request parameters validation error",
            404: "Package not found in database",
        },
    },
)
class routeUnpackagedDirs(Resource):
    @ns.expect(unpackaged_dirs_args)
    @ns.marshal_with(unpackaged_dirs_args_model)
    def get(self):
        args = unpackaged_dirs_args.parse_args(strict=True)
        url_logging(logger, g.url)
        wrk = UnpackagedDirs(g.connection, **args)
        if not wrk.check_params():
            abort(
                400,
                message=f"Request parameters validation error",
                args=args,
                validation_message=wrk.validation_results,
            )
        result, code = wrk.get()
        if code != 200:
            abort(code, **response_error_parser(result))
        return result, code


@ns.route(
    "/build_dependency_set",
    doc={
        "description": (
            "Get list of packages required for build by given "
            "packages list recursively"
        ),
        "responses": {
            400: "Request parameters validation error",
            404: "Requested data not found in database",
        },
    },
)
class routePackageBuildDependencySet(Resource):
    @ns.expect(build_dep_set_args)
    @ns.marshal_with(build_dep_set_model)
    def get(self):
        args = build_dep_set_args.parse_args(strict=True)
        url_logging(logger, g.url)
        wrk = PackageBuildDependencySet(g.connection, **args)
        if not wrk.check_params():
            abort(
                400,
                message=f"Request parameters validation error",
                args=args,
                validation_message=wrk.validation_results,
            )
        result, code = wrk.get()
        if code != 200:
            abort(code, **response_error_parser(result))
        return result, code


@ns.route("/repocop")
class routePackageRepocop(Resource):
    @ns.doc(
        description="Load repocop data into database",
        responses={
            201: "Data loaded",
            400: "Request parameters validation error",
            404: "Requested data not found in database",
        },
    )
    @ns.expect(repocop_json_list_model)
    @ns.doc(security="BasicAuth")
    @auth_required
    def post(self):
        args = {}
        url_logging(logger, g.url)
        wrk = Repocop(g.connection, json_data=request.json)
        if not wrk.check_params_post():
            abort(
                400,
                message=f"Request parameters validation error",
                args=args,
                validation_message=wrk.validation_results,
            )
        result, code = wrk.post()
        if code != 201:
            abort(code, **response_error_parser(result))
        return result, code

    @ns.doc(
        description="Get repocop data by name, version and release",
        responses={
            200: "Success",
            400: "Request parameters validation error",
            404: "Requested data not found in database",
        },
    )
    @ns.expect(pkg_repocop_args)
    @ns.marshal_with(repocop_json_get_list_model)
    def get(self):
        args = pkg_repocop_args.parse_args(strict=True)
        url_logging(logger, g.url)
        wrk = Repocop(g.connection, **args)
        if not wrk.check_params_get():
            abort(
                400,
                message=f"Request parameters validation error",
                args=args,
                validation_message=wrk.validation_results,
            )
        result, code = wrk.get()
        if code != 200:
            abort(code, **response_error_parser(result))
        return result, code


@ns.route(
    "/specfile_by_hash/<int:pkghash>",
    doc={
        "params": {"pkghash": "package hash"},
        "description": "Get spec file by source package hash",
        "responses": {
            400: "Request parameters validation error",
            404: "Package not found in database",
        },
    },
)
class routeSpecfileByPackageHash(Resource):
    pass

    @ns.expect()
    @ns.marshal_with(specfile_model)
    def get(self, pkghash):
        args = {}
        url_logging(logger, g.url)
        wrk = SpecfileByPackageHash(g.connection, pkghash, **args)
        if not wrk.check_params():
            abort(
                400,
                message=f"Request parameters validation error",
                args=args,
                validation_message=wrk.validation_results,
            )
        result, code = wrk.get()
        if code != 200:
            abort(code, **response_error_parser(result))
        return result, code


@ns.route(
    "/specfile_by_name",
    doc={
        "description": (
            "Get spec file by source package name and branch"
        ),
        "responses": {
            400: "Request parameters validation error",
            404: "Package not found in database",
        },
    },
)
class routeSpecfileByPackageName(Resource):
    @ns.expect(specfile_args)
    @ns.marshal_with(specfile_model)
    def get(self):
        args = specfile_args.parse_args(strict=True)
        url_logging(logger, g.url)
        wrk = SpecfileByPackageName(g.connection, **args)
        if not wrk.check_params():
            abort(
                400,
                message=f"Request parameters validation error",
                args=args,
                validation_message=wrk.validation_results,
            )
        result, code = wrk.get()
        if code != 200:
            abort(code, **response_error_parser(result))
        return result, code


@ns.route(
    "/package_files/<int:pkghash>",
    doc={
        "description": "Get package files by hash",
        "responses": {
            400: "Request parameters validation error",
            404: "Package not found in database",
        },
    },
)
class routeBinPackageFiles(Resource):
    # @ns.expect()
    @ns.marshal_with(package_files_model)
    def get(self, pkghash):
        url_logging(logger, g.url)
        wrk = PackageFiles(g.connection, pkghash)
        if not wrk.check_params():
            abort(
                400,
                message=f"Request parameters validation error",
                # args=args,
                validation_message=wrk.validation_results,
            )
        result, code = wrk.get()
        if code != 200:
            abort(code, **response_error_parser(result))
        return result, code
