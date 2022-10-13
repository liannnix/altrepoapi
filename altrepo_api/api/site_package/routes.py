# ALTRepo API
# Copyright (C) 2021-2022  BaseALT Ltd

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

from flask import g
from flask_restx import Resource

from altrepo_api.utils import get_logger, url_logging
from altrepo_api.api.base import run_worker, GET_RESPONSES_400_404

from .namespace import get_namespace
from .endpoints.package_info import (
    PackageInfo,
    DeletedPackageInfo,
    PackagesBinaryListInfo,
    PackageNVRByHash,
)
from .endpoints.logs import BinaryPackageLog
from .endpoints.changelog import PackageChangelog
from .endpoints.downloads import PackageDownloadLinks, BinaryPackageDownloadLinks
from .endpoints.versions import SourcePackageVersions, PackageVersions
from .endpoints.scripts import BinaryPackageScripts
from .endpoints.cve import LastPackagesWithCVEFix
from .parsers import (
    src_downloads_args,
    bin_downloads_args,
    package_chlog_args,
    package_info_args,
    pkgs_with_cve_fix_args,
    pkgs_binary_list_args,
    deleted_package_args,
    src_pkgs_versions_args,
    pkgs_versions_args,
    pkg_nvr_by_hash_args,
)
from .serializers import (
    package_chlog_model,
    package_info_model,
    deleted_package_model,
    last_pkgs_with_cve_fix_model,
    package_downloads_model,
    pkgs_binary_list_model,
    depends_packages_model,
    src_pkgs_versions_model,
    bin_package_log_el_model,
    pkg_nvr_by_hash_model,
)

ns = get_namespace()

logger = get_logger(__name__)


@ns.route(
    "/package_info/<int:pkghash>",
    doc={
        "params": {"pkghash": "package hash"},
        "description": "Get package info by hash",
        "responses": GET_RESPONSES_400_404,
    },
)
class routePackageInfo(Resource):
    @ns.expect(package_info_args)
    @ns.marshal_with(package_info_model)
    def get(self, pkghash):
        url_logging(logger, g.url)
        args = package_info_args.parse_args(strict=True)
        w = PackageInfo(g.connection, pkghash, **args)
        return run_worker(worker=w, args=args)


@ns.route(
    "/binary_package_archs_and_versions",
    doc={
        "description": "Get binary package archs and versions",
        "responses": GET_RESPONSES_400_404,
    },
)
class routePackagesBinaryList(Resource):
    @ns.expect(pkgs_binary_list_args)
    @ns.marshal_with(pkgs_binary_list_model)
    def get(self):
        url_logging(logger, g.url)
        args = pkgs_binary_list_args.parse_args(strict=True)
        w = PackagesBinaryListInfo(g.connection, **args)
        return run_worker(worker=w, args=args)


@ns.route(
    "/package_changelog/<int:pkghash>",
    doc={
        "params": {"pkghash": "package hash"},
        "description": "Get package changelog history by hash",
        "responses": GET_RESPONSES_400_404,
    },
)
class routePackageChangelog(Resource):
    pass

    @ns.expect(package_chlog_args)
    @ns.marshal_with(package_chlog_model)
    def get(self, pkghash):
        url_logging(logger, g.url)
        args = package_chlog_args.parse_args(strict=True)
        w = PackageChangelog(g.connection, pkghash, **args)
        return run_worker(worker=w, args=args)


@ns.route(
    "/deleted_package_info",
    doc={
        "description": ("Get information about package deleted from branch"),
        "responses": GET_RESPONSES_400_404,
    },
)
class routeDeletedPackageInfo(Resource):
    @ns.expect(deleted_package_args)
    @ns.marshal_with(deleted_package_model)
    def get(self):
        url_logging(logger, g.url)
        args = deleted_package_args.parse_args(strict=True)
        w = DeletedPackageInfo(g.connection, **args)
        return run_worker(worker=w, args=args)


@ns.route(
    "/binary_package_scripts/<int:pkghash>",
    doc={
        "description": "Get binary package scripts",
        "responses": GET_RESPONSES_400_404,
    },
)
class routeBinPackageScripts(Resource):
    # @ns.expect()
    @ns.marshal_with(depends_packages_model)
    def get(self, pkghash):
        url_logging(logger, g.url)
        args = {}
        w = BinaryPackageScripts(g.connection, pkghash, **args)
        return run_worker(worker=w, args=args)


@ns.route(
    "/last_packages_with_cve_fixed",
    doc={
        "description": (
            "Get information about last packages with CVE "
            "fixes mentioned in changelog"
        ),
        "responses": GET_RESPONSES_400_404,
    },
)
class routeLastPackagesWithCVEFix(Resource):
    @ns.expect(pkgs_with_cve_fix_args)
    @ns.marshal_with(last_pkgs_with_cve_fix_model)
    def get(self):
        url_logging(logger, g.url)
        args = pkgs_with_cve_fix_args.parse_args(strict=True)
        w = LastPackagesWithCVEFix(g.connection, **args)
        return run_worker(worker=w, args=args)


@ns.route(
    "/package_downloads/<int:pkghash>",
    "/package_downloads_src/<int:pkghash>",
    doc={
        "params": {"pkghash": "package hash"},
        "description": "Get package download links by source package hash",
        "responses": GET_RESPONSES_400_404,
    },
)
class routePackageDownloadLinks(Resource):
    @ns.expect(src_downloads_args)
    @ns.marshal_with(package_downloads_model)
    def get(self, pkghash):
        url_logging(logger, g.url)
        args = src_downloads_args.parse_args(strict=True)
        w = PackageDownloadLinks(g.connection, pkghash, **args)
        return run_worker(worker=w, args=args)


@ns.route(
    "/package_downloads_bin/<int:pkghash>",
    doc={
        "params": {"pkghash": "package hash"},
        "description": "Get binary package download link",
        "responses": GET_RESPONSES_400_404,
    },
)
class routeBinaryPackageDownloadLinks(Resource):
    @ns.expect(bin_downloads_args)
    @ns.marshal_with(package_downloads_model)
    def get(self, pkghash):
        url_logging(logger, g.url)
        args = bin_downloads_args.parse_args(strict=True)
        w = BinaryPackageDownloadLinks(g.connection, pkghash, **args)
        return run_worker(worker=w, args=args)


@ns.route(
    "/source_package_versions",
    doc={
        "description": "Get source package versions from last branches",
        "responses": GET_RESPONSES_400_404,
    },
)
class routeSourcePackageVersions(Resource):
    @ns.expect(src_pkgs_versions_args)
    @ns.marshal_with(src_pkgs_versions_model)
    def get(self):
        url_logging(logger, g.url)
        args = src_pkgs_versions_args.parse_args(strict=True)
        w = SourcePackageVersions(g.connection, **args)
        return run_worker(worker=w, args=args)


@ns.route(
    "/package_versions",
    doc={
        "description": "Get source or binary package versions from last branches",
        "responses": GET_RESPONSES_400_404,
    },
)
class routePackageVersions(Resource):
    @ns.expect(pkgs_versions_args)
    @ns.marshal_with(src_pkgs_versions_model)
    def get(self):
        url_logging(logger, g.url)
        args = pkgs_versions_args.parse_args(strict=True)
        w = PackageVersions(g.connection, **args)
        return run_worker(worker=w, args=args)


@ns.route(
    "/package_log_bin/<int:pkghash>",
    doc={
        "params": {"pkghash": "package hash"},
        "description": "Get binary package build log link",
        "responses": GET_RESPONSES_400_404,
    },
)
class routeBinaryPackageLog(Resource):
    @ns.expect()
    @ns.marshal_with(bin_package_log_el_model)
    def get(self, pkghash):
        url_logging(logger, g.url)
        args = {}
        w = BinaryPackageLog(g.connection, pkghash, **args)
        return run_worker(worker=w, args=args)


@ns.route(
    "/package_nvr_by_hash/<int:pkghash>",
    doc={
        "params": {"pkghash": "package hash"},
        "description": (
            "Get package name, version, release and type by hash. "
            "Check package name matching if provided."
        ),
        "responses": GET_RESPONSES_400_404,
    },
)
class routePackageNVRByHash(Resource):
    @ns.expect(pkg_nvr_by_hash_args)
    @ns.marshal_with(pkg_nvr_by_hash_model)
    def get(self, pkghash):
        url_logging(logger, g.url)
        args = pkg_nvr_by_hash_args.parse_args(strict=True)
        w = PackageNVRByHash(g.connection, pkghash, **args)
        return run_worker(worker=w, args=args)
