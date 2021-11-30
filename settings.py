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

import os
import getpass
import logging
from dataclasses import dataclass


@dataclass
class BasePathNamespace:
    PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
    # configuration parameters
    PROJECT_NAME = "altrepo_api"
    CONFIG_FILE = "/etc/{}/dbconfig.conf".format(PROJECT_NAME)
    LOG_FILE = "/home/{}/{}.log".format(getpass.getuser(), PROJECT_NAME)
    # application launch parameters
    DEFAULT_HOST = "127.0.0.1"
    DEFAULT_PORT = 5000
    WORKER_PROCESSES = "4"
    WORKER_TIMEOUT = "120"
    # database parameters
    DATABASE_HOST = "127.0.0.1"
    DATABASE_NAME = "default"
    TRY_CONNECTION_NUMBER = 5
    TRY_TIMEOUT = 5
    DATABASE_USER = "default"
    DATABASE_PASS = ""
    # debug settings
    FLASK_DEBUG = False
    SQL_DEBUG = False
    # logging settings
    LOG_LEVEL = logging.INFO
    # misc settings
    DEPENDENCY_MAX_DEPTH = 5
    # API admin credentials
    ADMIN_USER = "admin"
    # echo -n "SuperSecretPa\$\$w0rd" | sha512sum   # !! '$' symbol should be escaped in echo with backslash !!
    ADMIN_PASSWORD = ""


namespace = BasePathNamespace()
