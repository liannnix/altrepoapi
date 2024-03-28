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

import os
import sys
import logging
import configparser

from functools import partial

from .settings import namespace as settings


ACCESS_GROUPS_SECTION = "GROUPS"
# dictionary of config arguments
PARAMS = {
    "database": {
        "host": ("DATABASE_HOST", "str"),
        "port": ("DATABASE_PORT", "int"),
        "name": ("DATABASE_NAME", "str"),
        "try_numbers": ("TRY_CONNECTION_NUMBER", "int"),
        "try_timeout": ("TRY_TIMEOUT", "int"),
        "user": ("DATABASE_USER", "str"),
        "password": ("DATABASE_PASS", "str"),
    },
    "application": {
        "host": ("DEFAULT_HOST", "str"),
        "port": ("DEFAULT_PORT", "int"),
        "processes": ("WORKER_PROCESSES", "str"),
        "timeout": ("WORKER_TIMEOUT", "str"),
        "cors_origins": ("CORS_ORIGINS", "list"),
    },
    "other": {
        "admin_user": ("ADMIN_USER", "str"),
        "admin_password": ("ADMIN_PASSWORD", "str"),
        "admin_ldap_group": ("ADMIN_LDAP_GROUP", "str"),
        "log_file": ("LOG_FILE", "str"),
        "log_level": ("LOG_LEVEL", "log_level"),
        "sql_debug": ("SQL_DEBUG", "bool"),
        "log_to_file": ("LOG_TO_FILE", "bool"),
        "log_to_syslog": ("LOG_TO_SYSLOG", "bool"),
        "log_to_console": ("LOG_TO_CONSOLE", "bool"),
    },
    "ldap": {
        "ldap_server_uri": ("LDAP_SERVER_URI", "str"),
        "ldap_user_search": ("LDAP_USER_SEARCH", "str"),
        "ldap_require_group": ("LDAP_REQUIRE_GROUP", "str"),
    },
    "authentication": {
        "token_storage": ("TOKEN_STORAGE", "str"),
        "expires_access_token": ("EXPIRES_ACCESS_TOKEN", "int"),
        "expires_refresh_token": ("EXPIRES_REFRESH_TOKEN", "int"),
        "max_refresh_sessions_count": ("MAX_REFRESH_SESSIONS_COUNT", "int"),
        "auth_cookies_options": ("AUTH_COOKIES_OPTIONS", "str"),
    },
    "redis": {"redis_url": ("REDIS_URL", "str")},
    "errata": {"errata_id_url": ("ERRATA_ID_URL", "str")},
}


def read_config(
    config_file: str, params: dict[str, dict[str, tuple[str, str]]], namespace: object
) -> bool:
    config = configparser.ConfigParser(inline_comment_prefixes="#")

    # patch ConfigParser object
    def getlist(cls, section, option):
        value: str = cls.get(section, option)
        if not value:
            return None
        return [v.strip() for v in value.split(",") if v]

    setattr(config, "getlist", partial(getlist, config))

    if not config.read(config_file):
        return False

    def _log_level(section, option):
        ll = config.getint(section, option)
        if ll is None:
            return None
        if ll == 0:
            return logging.CRITICAL
        elif ll == 1:
            return logging.ERROR
        elif ll == 2:
            return logging.WARNING
        elif ll == 3:
            return logging.INFO
        elif ll == 4:
            return logging.DEBUG
        else:
            return logging.INFO

    conv = {
        "str": config.get,
        "int": config.getint,
        "bool": config.getboolean,
        "list": config.getlist,  # type: ignore
        "log_level": _log_level,
    }

    # update settings with values from config file
    for section in config.sections():
        # handle access groups section
        if section.upper() == ACCESS_GROUPS_SECTION:
            for option in config.options(section):
                key = None
                try:
                    key = namespace.AG[option.upper()]  # type: ignore
                except KeyError:
                    continue
                val = config.get(section, option)
                if key is not None and val:
                    namespace.ACCESS_GROUPS[key] = val  # type: ignore
            continue
        # handle other configuration sections
        for option in config.options(section):
            param = params.get(section.lower(), {}).get(option, None)
            if param is None:
                continue
            val = conv.get(param[1], config.get)(section, option)
            if val is not None:
                namespace.__setattr__(param[0], val)

    return True


# check python version
assert sys.version_info >= (3, 7), "Pyhton version 3.7 or newer is required!"

# abort to run as root
if os.geteuid() == 0:
    raise RuntimeError("It is not allowed to run application as root user!")

# try to get config file name from environment variable
cfg_file_env = os.getenv(settings.CONFIG_ENV_VAR)

# try to read config file in order of priority:
# command_line_argument -> environment_variable -> default
if len(sys.argv) >= 2 and os.path.isfile(sys.argv[1]):
    cfg_file = sys.argv[1]
elif cfg_file_env is not None and os.path.isfile(cfg_file_env):
    cfg_file = cfg_file_env
else:
    cfg_file = settings.CONFIG_FILE

# update settings with values from config file
if read_config(cfg_file, PARAMS, settings):
    print(f"*** Run ALTRepo API with config from {cfg_file} ***")
else:
    raise RuntimeError("Failed to read configuration from {0}".format(cfg_file))
