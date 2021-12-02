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
import sys
import logging
import configparser
from gunicorn.app.wsgiapp import run

from settings import namespace as settings

# dictionary of config arguments
PARAMS = {
    "database": {
        "host": ("DATABASE_HOST", "str"),
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
    },
    "other": {
        "admin_user": ("ADMIN_USER", "str"),
        "admin_password": ("ADMIN_PASSWORD", "str"),
        "log_file": ("LOG_FILE", "str"),
        "log_level": ("LOG_LEVEL", "log_level"),
        "sql_debug": ("SQL_DEBUG", "bool"),
        "log_to_file": ("LOG_TO_FILE", "bool"),
        "log_to_syslog": ("LOG_TO_SYSLOG", "bool"),            
    },
}


def read_config(config_file: str, params: dict, namespace: object) -> bool:
    config = configparser.ConfigParser(inline_comment_prefixes="#")

    if not config.read(config_file):
        return False

    def _log_level(section, option):
        ll = config.getint(section, option)
        if ll is None :
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
        "log_level": _log_level
    }

    # update settings with values from config file
    for section in config.sections():
        for option in config.options(section):
            param = params.get(section.lower(), {}).get(option, None)
            if param is None:
                continue
            val = conv.get(param[1], config.get)(section, option)
            if val is not None:
                namespace.__setattr__(param[0], val)

    return True


def start():
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

    sys.argv = [
        sys.argv[0],
        "-b",
        "{}:{:d}".format(settings.DEFAULT_HOST, settings.DEFAULT_PORT),
        "-w",
        settings.WORKER_PROCESSES,
        "app:app",
        "--timeout",
        settings.WORKER_TIMEOUT,
    ]

    run()
