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

from werkzeug.exceptions import Unauthorized, Forbidden

class ApiUnauthorized(Unauthorized):
    """Raise status code 401 with customizable WWW-Authenticate header."""

    def __init__(
        self,
        description="Unauthorized",
        admin_only=False,
        error=None,
        error_description=None,
    ):
        self.description = description
        self.admin_only = admin_only
        self.error = error
        self.error_description = error_description
        Unauthorized.__init__(
            self, description=description, response=None, www_authenticate=None
        )


class ApiForbidden(Forbidden):
    """Raise status code 403 with WWW-Authenticate header."""

    description = "You are not an administrator"
