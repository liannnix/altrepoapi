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

import hashlib
import base64
from collections import namedtuple

from altrepo_api.settings import namespace
from altrepo_api.utils import get_logger

logger = get_logger(__name__)

AuthCheckResult = namedtuple("AuthCheckResult", ["verified", "error", "value"])

def check_auth(token):
    try:
        token = token.split()[1].strip()
        user, password = base64.b64decode(token).decode("utf-8").split(':')
        passwd_hash = hashlib.sha512(password.encode("utf-8")).hexdigest()
        
        logger.info(f"User '{user}' attempt to authorize")

        if user == namespace.ADMIN_USER and passwd_hash == namespace.ADMIN_PASSWORD:
            logger.info(f"User '{user}' successfully authorized")
            return AuthCheckResult(True, "OK", {"user": user})
        else:
            logger.warning(f"User '{user}' authorization failed")
            return AuthCheckResult(False, "authorization failed", {})
    except:
        logger.error(f"Authorization token validation error")
        return AuthCheckResult(False, "token validation error", {})
