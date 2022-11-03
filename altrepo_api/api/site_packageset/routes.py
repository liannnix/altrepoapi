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
from .endpoints.find_src_package import FindSourcePackageInBranch
from .endpoints.find_package import (
    PackagesetFindPackages,
    FastPackagesSearchLookup,
    PackagesetPkghashByNVR,
)
from .endpoints.package_hash import (
    PackagesetPackageHash,
    PackagesetPackageBinaryHash,
)
from .endpoints.pkgset_packages import (
    PackagesetPackages,
    AllPackagesetsByHash,
    LastBranchPackages,
)
from .parsers import (
    pkgs_by_name_args,
    pkgset_pkghash_args,
    pkgset_packages_args,
    last_pkgs_branch_args,
    pkgset_pkghash_by_nvr,
    pkgset_pkg_binary_hash_args,
    pkgs_search_by_name_args,
    find_src_pkg_args,
)
from .serializers import (
    pkgset_packages_model,
    pkgset_pkghash_model,
    fing_pkgs_by_name_model,
    pkgsets_by_hash_model,
    last_packages_branch_model,
    fast_pkgs_search_model,
    pkgset_pkghash_by_nvr_model,
    find_src_pkg_in_branch_model,
)

ns = get_namespace()

logger = get_logger(__name__)


@ns.route(
    "/repository_packages",
    doc={
        "description": (
            "Get list of packageset packages in accordance to given parameters"
        ),
        "responses": GET_RESPONSES_400_404,
    },
)
class routePackagesetPackages(Resource):
    @ns.expect(pkgset_packages_args)
    @ns.marshal_with(pkgset_packages_model)
    def get(self):
        url_logging(logger, g.url)
        args = pkgset_packages_args.parse_args(strict=True)
        w = PackagesetPackages(g.connection, **args)
        return run_worker(worker=w, args=args)


@ns.route(
    "/pkghash_by_name",
    doc={
        "description": ("Get source package hash by package name and package set name"),
        "responses": GET_RESPONSES_400_404,
    },
)
class routePackagesetPackageHash(Resource):
    @ns.expect(pkgset_pkghash_args)
    @ns.marshal_with(pkgset_pkghash_model)
    def get(self):
        url_logging(logger, g.url)
        args = pkgset_pkghash_args.parse_args(strict=True)
        w = PackagesetPackageHash(g.connection, **args)
        return run_worker(worker=w, args=args)


@ns.route(
    "/pkghash_by_binary_name",
    doc={
        "description": (
            "Get binary package hash by package name, arch and package set name"
        ),
        "responses": GET_RESPONSES_400_404,
    },
)
class routePackagesetPackageBinaryHash(Resource):
    @ns.expect(pkgset_pkg_binary_hash_args)
    @ns.marshal_with(pkgset_pkghash_model)
    def get(self):
        url_logging(logger, g.url)
        args = pkgset_pkg_binary_hash_args.parse_args(strict=True)
        w = PackagesetPackageBinaryHash(g.connection, **args)
        return run_worker(worker=w, args=args)


@ns.route(
    "/find_packages",
    doc={
        "description": "Find packages by name",
        "responses": GET_RESPONSES_400_404,
    },
)
class routePackagesetFindPackages(Resource):
    @ns.expect(pkgs_by_name_args)
    @ns.marshal_with(fing_pkgs_by_name_model)
    def get(self):
        url_logging(logger, g.url)
        args = pkgs_by_name_args.parse_args(strict=True)
        w = PackagesetFindPackages(g.connection, **args)
        return run_worker(worker=w, args=args)


@ns.route(
    "/fast_packages_search_lookup",
    doc={
        "description": "Fast packages search by name",
        "responses": GET_RESPONSES_400_404,
    },
)
class routePackagesetFastPackagesSearch(Resource):
    @ns.expect(pkgs_search_by_name_args)
    @ns.marshal_with(fast_pkgs_search_model)
    def get(self):
        url_logging(logger, g.url)
        args = pkgs_by_name_args.parse_args(strict=True)
        w = FastPackagesSearchLookup(g.connection, **args)
        return run_worker(worker=w, args=args)


@ns.route(
    "/last_packages_by_branch",
    doc={
        "description": ("Get list of last packages from branch for given parameters"),
        "responses": GET_RESPONSES_400_404,
    },
)
class routeLastBranchPackages(Resource):
    @ns.expect(last_pkgs_branch_args)
    @ns.marshal_with(last_packages_branch_model)
    def get(self):
        url_logging(logger, g.url)
        args = last_pkgs_branch_args.parse_args(strict=True)
        w = LastBranchPackages(g.connection, **args)
        return run_worker(worker=w, args=args)


@ns.route(
    "/packagesets_by_hash/<int:pkghash>",
    doc={
        "params": {"pkghash": "package hash"},
        "description": "Get package set list by package hash",
        "responses": GET_RESPONSES_400_404,
    },
)
class routePackagsetsByHash(Resource):
    pass

    @ns.expect()
    @ns.marshal_with(pkgsets_by_hash_model)
    def get(self, pkghash):
        url_logging(logger, g.url)
        args = {}
        w = AllPackagesetsByHash(g.connection, pkghash, **args)
        return run_worker(worker=w, args=args)


@ns.route(
    "/pkghash_by_nvr",
    doc={
        "description": (
            "Get source package hash by package name, version and release"
            " for specific branch"
        ),
        "responses": GET_RESPONSES_400_404,
    },
)
class routePackagesetPkghashByNVR(Resource):
    @ns.expect(pkgset_pkghash_by_nvr)
    @ns.marshal_with(pkgset_pkghash_by_nvr_model)
    def get(self):
        url_logging(logger, g.url)
        args = pkgset_pkghash_by_nvr.parse_args(strict=True)
        w = PackagesetPkghashByNVR(g.connection, **args)
        return run_worker(worker=w, args=args)


@ns.route(
    "/find_source_package",
    doc={
        "description": (
            "Find source package in branch."
        ),
        "responses": GET_RESPONSES_400_404,
    },
)
class routeFindSourcePackage(Resource):
    @ns.expect(find_src_pkg_args)
    @ns.marshal_with(find_src_pkg_in_branch_model)
    def get(self):
        url_logging(logger, g.url)
        args = find_src_pkg_args.parse_args(strict=True)
        w = FindSourcePackageInBranch(g.connection, **args)
        return run_worker(worker=w, args=args)
