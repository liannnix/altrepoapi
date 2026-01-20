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
import mmh3
import re
import sys
import time

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from flask import Response, request, send_file, __version__ as FLASK_VERSION
from logging import handlers
from packaging import version
from typing import Any, Iterable, TypeVar, Union
from urllib.parse import unquote
from uuid import UUID, uuid4

from altrepo_api.settings import namespace as settings


@dataclass(frozen=True)
class logger_level:
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL


def json_default(obj):
    # convert datetime to ISO string representation
    if isinstance(obj, datetime):
        return obj.isoformat()
    # convert UUID to string
    if isinstance(obj, UUID):
        return str(obj)

    return obj


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

        if settings.LOG_TO_CONSOLE:
            # stderr handler config
            fmt = logging.Formatter("%(levelname)-9s: %(message)s")

            err_handler = logging.StreamHandler(sys.stderr)
            err_handler.setLevel(logging.ERROR)
            err_handler.setFormatter(fmt)

            info_handler = logging.StreamHandler(sys.stdout)
            info_handler.setLevel(settings.LOG_LEVEL)
            info_handler.addFilter(lambda rec: rec.levelno < logging.ERROR)
            info_handler.setFormatter(fmt)

            root_logger.addHandler(err_handler)
            root_logger.addHandler(info_handler)

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
        details = {
            k: v for k, v in response.items() if k not in ("message", "error", "Error")
        }
        return {"message": msg, "details": details}
    except AttributeError:
        return {"message": response}


def convert_to_dict(keys: list[Any], values: list[Any]) -> dict[Any, Any]:
    res = {}

    for i in range(len(values)):
        res[i] = dict([(keys[j], values[i][j]) for j in range(len(values[i]))])

    return res


def join_tuples(tuple_list: list[tuple[Any, ...]]) -> tuple[Any, ...]:
    return tuple([tuple_[0] for tuple_ in tuple_list])


# convert tuple or list of tuples to dict by set keys
def tuplelist_to_dict(
    tuplelist: Iterable[tuple[Any, ...]], num: int
) -> dict[Any, list[Any]]:
    result_dict = defaultdict(list)
    for tpl in tuplelist:
        data = tpl[1] if num == 1 else tpl[1 : num + 1]

        if isinstance(data, tuple):
            result_dict[tpl[0]] += list(data)
        elif isinstance(data, list):
            result_dict[tpl[0]] += data
        else:
            result_dict[tpl[0]].append(data)

    return result_dict


def remove_duplicate(list_: list[Any]) -> list[Any]:
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


def datetime_to_iso(dt: datetime) -> str:
    return dt.isoformat()


_TZ_UTC = timezone.utc
_TZ_LOCAL = datetime.now().astimezone(None).tzinfo
DT_NEVER = datetime.fromtimestamp(0, tz=timezone.utc)


def datetime_to_tz_aware(dt: datetime) -> datetime:
    """Checks if datetime object is timezone aware.
    Converts timezone naive datetime to aware one assuming timezone is
    equal to local one for API host."""

    if dt.tzinfo is not None and dt.tzinfo.utcoffset is not None:
        # datetime object is timezone aware
        return dt

    # datetime object is timezone naive
    return dt.replace(tzinfo=_TZ_LOCAL).astimezone(_TZ_UTC)


def sort_branches(branches: Iterable[str]) -> tuple[str, ...]:
    """Use predefined sort list order for branch sorting."""
    res = []
    branches = set(branches)
    sort_list = [
        "sisyphus",
        "sisyphus_e2k",
        "sisyphus_mipsel",
        "sisyphus_riscv64",
        "sisyphus_loongarch64",
        "p11",
        "p10",
        "p10_e2k",
        "p9",
        "p9_e2k",
        "p9_mipsel",
        "p8",
        "p7",
        "p6",
        "p5",
        "c10f2",
        "c10f1",
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


def dp_flags_decode(dp_flag: int, dp_decode_table: list[str]) -> list[str]:
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

    def rwx(perms: int) -> str:
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

    def file_permissions(perms: int) -> str:
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


def make_tmp_table_name(name: str) -> str:
    """Generates quite unique temporary table name."""
    return f"_tmp_{name}_{str(uuid4()).split('-')[-1]}"


def arch_sort_index(arch: str) -> int:
    return {
        "src": 0,
        "noarch": -1,
        "x86_64": -2,
        "i586": -3,
        "aarch64": -4,
        "armh": -5,
        "ppc64le": -6,
        "riscv64": -7,
        "loongarch64": -8,
        "mipsel": -9,
        "e2k": -10,
        "e2kv4": -11,
        "e2kv5": -12,
        "e2kv6": -13,
        "x86_64-i586": -14,
    }.get(arch, -100)


def get_real_ip() -> str:
    """Get real user IP from 'X-Forwarded-For' header set by proxy if available."""

    x_forwarded_for = request.headers.get("X-Forwarded-For")

    if not x_forwarded_for:
        ip = request.remote_addr
    else:
        ip = x_forwarded_for.split(",", maxsplit=1)[0].strip()

    return ip or "unknown"


def valid_task_id(task_id: int) -> bool:
    """Validate that 'task_id' is an integer and within a valid range."""

    MIN_TASK_ID = 1
    MAX_TASK_ID = 4_000_000_000

    return task_id >= MIN_TASK_ID and task_id <= MAX_TASK_ID


def make_snowflake_id(timestamp: Union[int, datetime], lower_32bit) -> int:
    """
    Returns a 64-bit Snowflake-like ID using a custom epoch,
    with timestamp (int or datetime) in the upper 32 bits
    and lower_32bit (masked to 32 bits) in the lower bits.
    """
    EPOCH = 1_000_000_000

    if isinstance(timestamp, datetime):
        timestamp = int(timestamp.timestamp())

    return ((timestamp - EPOCH) << 32) | (lower_32bit & 0xFFFFFFFF)


T = TypeVar("T")


def get_nested_value(
    data: dict[str, Any], key_path: str, default: T = None
) -> Union[Any, T]:
    """Traverses a nested dictionary and returns the value at the given key path."""

    if not data or not key_path:
        return default

    keys = key_path.split(".")
    current = data

    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]

    return current
