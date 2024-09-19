# ALTRepo API
# Copyright (C) 2021-2024  BaseALT Ltd

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

from altrepo_api.api.parser import parser, packager_nick_type, password_type

nickname = parser.register_item(
    "nickname",
    type=packager_nick_type,
    required=True,
    help="User nickname",
    location="form",
)

password = parser.register_item(
    "password",
    type=password_type,
    required=True,
    help="User password",
    location="form",
)
token = parser.register_item(
    "access_token",
    type=str,
    required=True,
    help="Access token",
    location="form",
)

login_args = parser.build_parser(nickname, password)
refresh_token_args = parser.build_parser(token)
