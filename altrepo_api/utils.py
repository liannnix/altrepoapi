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

import datetime
import json
import logging
import mmh3
import re
import time

from collections import defaultdict
from dataclasses import dataclass
from flask import send_file, __version__ as FLASK_VERSION
from flask.wrappers import Response
from logging import handlers
from packaging import version
from typing import Any, Iterable, Union
from urllib.parse import unquote
from uuid import UUID

from altrepo_api.settings import namespace as settings


@dataclass(frozen=True)
class logger_level:
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL


class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        # convert datetime to ISO string representation
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        # convert UUID to string
        if isinstance(obj, UUID):
            return str(obj)

        return json.JSONEncoder.default(self, obj)


def mmhash(val: Any) -> int:
    a, b = mmh3.hash64(val, signed=False)
    return a ^ b


def get_logger(name: str) -> logging.Logger:
    """Get logger instance with specific name as child of root logger.
    Creates root logger if it doesn't exists."""

    root_logger = logging.getLogger(settings.PROJECT_NAME)
    root_logger.setLevel(settings.LOG_LEVEL)

    if not len(root_logger.handlers):
        if settings.LOG_TO_SYSLOG:
            # syslog handler config
            if settings.LOG_LEVEL == logging.DEBUG:
                fmt = logging.Formatter(
                    ": %(levelname)-9s%(name)s %(module)s %(funcName)s %(lineno)d\t%(message)s"
                )
            else:
                fmt = logging.Formatter(": %(levelname)-9s%(message)s")

            syslog_handler = handlers.SysLogHandler(
                address="/dev/log", facility=handlers.SysLogHandler.LOG_DAEMON
            )
            syslog_handler.ident = settings.PROJECT_NAME
            syslog_handler.setFormatter(fmt)

            root_logger.addHandler(syslog_handler)

        if settings.LOG_TO_FILE:
            # file handler config
            fmt = logging.Formatter(
                "%(asctime)s\t%(levelname)s\t%(name)s %(module)s %(funcName)s %(lineno)d\t%(message)s"
            )

            file_handler = handlers.RotatingFileHandler(
                filename=settings.LOG_FILE, maxBytes=2**26, backupCount=1
            )
            file_handler.setFormatter(fmt)

            root_logger.addHandler(file_handler)
        # pass if no logging handlers enabled
        pass

    logger_name = ".".join((settings.PROJECT_NAME, name))
    logger = logging.getLogger(logger_name)

    return logger


def exception_to_logger(exception: Exception) -> str:
    return exception.args[0].split("\n")[0]


def url_logging(logger: logging.Logger, url: Any) -> None:
    logger.info(unquote(url))


# return error message as json format
def json_str_error(error: Any) -> dict[str, Any]:
    return {"Error": error}


def response_error_parser(response: Any) -> dict[str, Any]:
    try:
        msg = response.get("message")
        if not msg:
            msg = response.get("error") or response.get("Error")
        details = [
            {k: v}
            for k, v in response.items()
            if k not in ("message", "error", "Error")
        ]
        return {"message": msg, "details": details}
    except AttributeError:
        return {"message": response}


def convert_to_dict(keys: list, values: list) -> dict:
    res = {}

    for i in range(len(values)):
        res[i] = dict([(keys[j], values[i][j]) for j in range(len(values[i]))])

    return res


def convert_to_json(keys: list, values: list, sort: bool = False) -> str:
    js = {}

    for i in range(len(values)):
        js[i] = dict([(keys[j], values[i][j]) for j in range(len(values[i]))])

        for key in js[i]:
            if key == "date":
                js[i]["date"] = datetime.datetime.strftime(
                    js[i]["date"], "%Y-%m-%d %H:%M:%S"
                )

    return json.dumps(js, sort_keys=sort)


def join_tuples(tuple_list: list) -> tuple:
    return tuple([tuple_[0] for tuple_ in tuple_list])


# convert tuple or list of tuples to dict by set keys
def tuplelist_to_dict(tuplelist: list, num: int) -> dict:
    result_dict = defaultdict(list)
    for tuple_ in tuplelist:
        count = tuple_[1] if num == 1 else tuple_[1 : num + 1]

        if isinstance(count, tuple):
            result_dict[tuple_[0]] += [elem for elem in count]
        elif isinstance(count, list):
            result_dict[tuple_[0]] += count
        else:
            result_dict[tuple_[0]].append(count)

    return result_dict


def remove_duplicate(list_: list) -> list:
    return list(set(list_))


def func_time(logger: logging.Logger):
    def decorator(function):
        def wrapper(*args, **kwargs):
            start = time.time()
            resuls = function(*args, **kwargs)
            logger.info("Time {} is {}".format(function.__name__, time.time() - start))
            return resuls

        wrapper.__name__ = function.__name__
        return wrapper

    return decorator


def datetime_to_iso(dt: datetime.datetime) -> str:
    return dt.isoformat()


def sort_branches(branches: Iterable) -> tuple:
    """Use predefined sort list order for branch sorting."""
    res = []
    branches = set(branches)
    sort_list = [
        "sisyphus",
        "sisyphus_e2k",
        "sisyphus_mipsel",
        "sisyphus_riscv64",
        "p10",
        "p10_e2k",
        "p9",
        "p9_e2k",
        "p9_mipsel",
        "p8",
        "p7",
        "p6",
        "p5",
        "c9f2",
        "c9f1",
        "c9m2",
        "c9m1",
        "c8.1",
        "c8",
        "c7.1",
        "c7",
        "c6",
        "t7",
        "t6",
        "5.1",
        "5.0",
        "4.1",
        "4.0",
    ]
    # add branches to result in accordance to sort_list order
    for branch in sort_list:
        if branch in branches:
            res.append(branch)
    # fall back: add branches from input that are missing from sort_list
    diff = branches - set(res)
    res += sorted([x for x in diff], reverse=True)
    return tuple(res)


def get_nickname_from_packager(packager: str) -> str:
    email_match = re.compile("(<.+@?.+>)+")
    m = email_match.search(packager)
    if m is None:
        # return original string if no regex match found
        return packager
    email_ = m.group(1).strip().replace(" at ", "@")
    email_ = email_.lstrip("<")
    nickname = email_.split("@")[0]
    return nickname


def dp_flags_decode(dp_flag: int, dp_decode_table: list) -> list[str]:
    res = []
    if dp_flag < 0:
        return []
    if dp_flag == 0:
        res = [dp_decode_table[0]]
        return res
    x = dp_flag
    pos = 1
    while x > 0 and pos < len(dp_decode_table):
        if x & 0x1:
            res.append(dp_decode_table[pos])
        x = x >> 1
        pos += 1
    return res


def full_file_permissions(file_type: str, file_mode: int) -> str:
    res = ""
    types = {
        "file": "-",
        "directory": "d",
        "symlink": "l",
        "socket": "s",
        "block": "b",
        "char": "c",
        "fifo": "p",
    }

    def rwx(perms):
        res = ""
        if perms & 0x04:
            res += "r"
        else:
            res += "-"
        if perms & 0x02:
            res += "w"
        else:
            res += "-"
        if perms & 0x01:
            res += "x"
        else:
            res += "-"
        return res

    def file_permissions(perms):
        flags = (perms >> 9) & 0x07
        res = ""
        for i in range(3):
            p = (perms >> (i * 3)) & 0x07
            # execution bit
            rwx_ = rwx(p)
            x_ = rwx_[2]
            # SUID
            if i == 2 and (flags & 0x04):
                x_ = "s" if p & 0x01 else "S"
            # SGID
            if i == 1 and (flags & 0x02):
                x_ = "s" if p & 0x01 else "S"
            # sticky bit
            if i == 0 and (flags & 0x01):
                x_ = "t" if p & 0x01 else "T"
            res = rwx_[:2] + x_ + res
        return res

    res = file_permissions(file_mode)
    res = types[file_type] + res

    return res


def bytes2human(size: Union[int, float]) -> str:
    """Convert file size in bytes to human readable string representation."""
    for unit in ["", "K", "M", "G", "T", "P", "E"]:
        if abs(size) < 1024.0:
            return f"{size:3.1f} {unit}B"
        size /= 1024.0
    return f"{size:.1f} ZB"


FLASK_BREAKING_CHANGE_VERSION = "2.2.0"


def send_file_compat(
    *,
    file: str,
    mimetype: str,
    as_attachment: bool,
    attachment_filename: str,
) -> Response:
    # check the version of Flask imported
    flask_version = version.parse(FLASK_VERSION)
    if flask_version < version.parse(FLASK_BREAKING_CHANGE_VERSION):
        # use old 'send_file' arguments names
        return send_file(
            file,
            mimetype=mimetype,
            as_attachment=as_attachment,
            attachment_filename=attachment_filename,  # type: ignore
        )
    # use new 'send_file' arguments names
    return send_file(
        file,
        mimetype=mimetype,
        as_attachment=as_attachment,
        download_name=attachment_filename,
    )
