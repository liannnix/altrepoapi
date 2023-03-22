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
from .endpoints.groups import AclGroups
from .endpoints.packages import AclByPackages
from .parsers import acl_groups_args, acl_by_packages_args
from .serializers import acl_groups_model, acl_by_packages_model

ns = get_namespace()

logger = get_logger(__name__)


@ns.route("/groups")
@ns.doc(
    description="List of ACL groups for specific branch",
    responses=GET_RESPONSES_400_404,
)
class routeAclGroups(Resource):
    @ns.expect(acl_groups_args)
    @ns.marshal_list_with(acl_groups_model)
    def get(self):
        url_logging(logger, g.url)
        args = acl_groups_args.parse_args(strict=True)
        w = AclGroups(g.connection, **args)
        return run_worker(worker=w, args=args)


@ns.route("/by_packages")
@ns.doc(
    description="ACL groups for source packages list in specific branch",
    responses=GET_RESPONSES_400_404,
)
class routeAclByPackages(Resource):
    @ns.expect(acl_by_packages_args)
    @ns.marshal_list_with(acl_by_packages_model)
    def get(self):
        url_logging(logger, g.url)
        args = acl_by_packages_args.parse_args(strict=True)
        w = AclByPackages(g.connection, **args)
        return run_worker(worker=w, args=args)
