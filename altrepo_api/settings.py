# ALTRepo API
# Copyright (C) 2021-2025  BaseALT Ltd

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

import logging
import os

from dataclasses import dataclass
from enum import Enum, auto


class AccessGroups(Enum):
    API_ADMIN = auto()
    API_USER = auto()
    CVE_ADMIN = auto()
    CVE_USER = auto()


AG_ALL = [
    AccessGroups.API_ADMIN,
    AccessGroups.API_USER,
    AccessGroups.CVE_ADMIN,
    AccessGroups.CVE_USER,
]


@dataclass
class BasePathNamespace:
    PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
    # configuration parameters
    CONFIG_ENV_VAR = "ALTREPO_API_CONFIG"
    PROJECT_NAME = "altrepo-api"
    CONFIG_FILE = "/etc/{}/api.conf".format(PROJECT_NAME)
    LOG_FILE = "/var/log/{}/log".format(PROJECT_NAME)
    # endpoint response OK code check settings
    OK_RESPONSE_CODES = (200, 201, 202, 204)
    OK_RESPONSE_CODE_STRICT_CHECK = False
    # application launch parameters
    DEFAULT_HOST = "127.0.0.1"
    DEFAULT_PORT = 5000
    WORKER_PROCESSES = "1"
    WORKER_TIMEOUT = "30"
    # database parameters
    DATABASE_HOST = "127.0.0.1"
    DATABASE_PORT = 9000
    DATABASE_NAME = "default"
    TMP_DATABASE_NAME = ""
    TRY_CONNECTION_NUMBER = 5
    TRY_TIMEOUT = 5
    DATABASE_USER = "default"
    DATABASE_PASS = ""
    # debug settings
    FLASK_DEBUG = False
    SQL_DEBUG = False
    # logging settings
    LOG_LEVEL = logging.INFO
    LOG_TO_FILE = False
    LOG_TO_SYSLOG = False
    LOG_TO_CONSOLE = True
    # misc settings
    DEPENDENCY_MAX_DEPTH = 5
    # API admin credentials
    ADMIN_USER = "admin"
    ADMIN_PASSWORD = ""  # XXX: echo -n "SuperSecretPa\$\$w0rd" | sha512sum   # !! '$' symbol should be escaped in echo with backslash !!
    # authentication using LDAP server
    LDAP_SERVER_URI = ""
    LDAP_USER_SEARCH = ""
    LDAP_REQUIRE_GROUP = ""
    # LDAP access groups
    AG = AccessGroups  # used in tests only
    ACCESS_GROUPS = {g: "" for g in AccessGroups}
    # authentication token settings
    TOKEN_STORAGE = "file"  # {file | redis}
    EXPIRES_ACCESS_TOKEN = 60 * 5  # access token storage time in seconds
    EXPIRES_REFRESH_TOKEN = 60 * 60 * 12  # refresh token storage time in seconds
    MAX_REFRESH_SESSIONS_COUNT = 2
    # redis
    REDIS_URL = ""
    # errata service
    ERRATA_ID_URL = ""
    # Flask CORS origins
    CORS_ORIGINS = "*"
    AUTH_COOKIES_OPTIONS = "HttpOnly;"


namespace = BasePathNamespace()
