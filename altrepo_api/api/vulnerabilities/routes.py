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

from flask import g
from flask_restx import Resource

from altrepo_api.utils import get_logger, url_logging
from altrepo_api.api.base import run_worker, GET_RESPONSES_400_404

from .namespace import get_namespace
from .parsers import (
    cve_info_args,
    bdu_info_args,
    cve_vulnerable_packages_args,
    bdu_vulnerable_packages_args,
)
from .serializers import vulnerability_info_model, cve_packages_model
from .endpoints.vuln import VulnInfo
from .endpoints.cve import VulnerablePackageByCve

ns = get_namespace()

logger = get_logger(__name__)


@ns.route(
    "/cve",
    doc={
        "description": "Get CVE information",
        "responses": GET_RESPONSES_400_404,
    },
)
class routeCveInfo(Resource):
    @ns.expect(cve_info_args)
    @ns.marshal_with(vulnerability_info_model)
    def get(self):
        url_logging(logger, g.url)
        args = cve_info_args.parse_args(strict=True)
        w = VulnInfo(g.connection, **args)
        return run_worker(worker=w, args=args)


@ns.route(
    "/cve/packages",
    doc={
        "description": "Get CVE vulnerabilty information for packages in latest branch state",
        "responses": GET_RESPONSES_400_404,
    },
)
class routeVulnerablePackageByCve(Resource):
    @ns.expect(cve_vulnerable_packages_args)
    @ns.marshal_with(cve_packages_model)
    def get(self):
        url_logging(logger, g.url)
        args = cve_vulnerable_packages_args.parse_args(strict=True)
        w = VulnerablePackageByCve(g.connection, **args)
        return run_worker(worker=w, args=args)


@ns.route(
    "/bdu/packages",
    doc={
        "description": "Get BDU vulnerabilty information for packages in latest branch state",
        "responses": GET_RESPONSES_400_404,
    },
)
class routeVulnerablePackageByBdu(Resource):
    @ns.expect(bdu_vulnerable_packages_args)
    @ns.marshal_with(cve_packages_model)
    def get(self):
        url_logging(logger, g.url)
        args = bdu_vulnerable_packages_args.parse_args(strict=True)
        w = VulnerablePackageByCve(g.connection, **args)
        return run_worker(worker=w, run_method=w.get_by_bdu, args=args)


@ns.route(
    "/bdu",
    doc={
        "description": "Get BDU information",
        "responses": GET_RESPONSES_400_404,
    },
)
class routeBduInfo(Resource):
    @ns.expect(bdu_info_args)
    @ns.marshal_with(vulnerability_info_model)
    def get(self):
        url_logging(logger, g.url)
        args = bdu_info_args.parse_args(strict=True)
        w = VulnInfo(g.connection, **args)
        return run_worker(worker=w, args=args)
