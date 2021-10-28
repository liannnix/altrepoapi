import re
from typing import List

import mmh3
import json
import time
import logging
from logging import handlers
import datetime
import argparse
import configparser
from collections import defaultdict
from urllib.parse import unquote
from dataclasses import dataclass


from settings import namespace as settings


@dataclass(frozen=True)
class logger_level:
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL


def mmhash(val):
    a, b = mmh3.hash64(val, signed=False)
    return a ^ b


def get_logger(name):
    """Get logger instance with specific name as child of root logger.
    Creates root logger if it doesn't exists."""

    root_logger = logging.getLogger(settings.PROJECT_NAME)
    root_logger.setLevel(settings.LOG_LEVEL)

    if not len(root_logger.handlers):
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

        # file handler config
        fmt = logging.Formatter(
            "%(asctime)s\t%(levelname)s\t%(name)s %(module)s %(funcName)s %(lineno)d\t%(message)s"
        )

        file_handler = handlers.RotatingFileHandler(
            filename=settings.LOG_FILE, maxBytes=2 ** 26, backupCount=10
        )
        file_handler.setFormatter(fmt)

        root_logger.addHandler(syslog_handler)
        root_logger.addHandler(file_handler)

    logger_name = ".".join((settings.PROJECT_NAME, name))
    logger = logging.getLogger(logger_name)

    return logger


def exception_to_logger(exception):
    return exception.args[0].split("\n")[0]


def read_config(config_file):
    config = configparser.ConfigParser(inline_comment_prefixes="#")

    if config.read(config_file):
        return config

    return False


def url_logging(logger, url):
    logger.info(unquote(url))


# return error message as json format
def json_str_error(error):
    return {"Error": error}


def response_error_parser(response):
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
    except:
        return {"message": response}


def convert_to_dict(keys, values):
    res = {}

    for i in range(len(values)):
        res[i] = dict([(keys[j], values[i][j]) for j in range(len(values[i]))])

    return res


def convert_to_json(keys, values, sort=False):
    js = {}

    for i in range(len(values)):
        js[i] = dict([(keys[j], values[i][j]) for j in range(len(values[i]))])

        for key in js[i]:
            if key == "date":
                js[i]["date"] = datetime.datetime.strftime(
                    js[i]["date"], "%Y-%m-%d %H:%M:%S"
                )

    return json.dumps(js, sort_keys=sort)


def join_tuples(tuple_list):
    return tuple([tuple_[0] for tuple_ in tuple_list])


def print_statusbar(message_list):
    types = {
        "i": "[INFO]",
        "w": "[WARNING]",
        "d": "[DEBUG]",
        "e": "[ERROR]",
    }

    for msg in message_list:
        print(
            "[ALTREPO SERVER]{type_}: {msg}" "".format(type_=types[msg[1]], msg=msg[0])
        )


def make_argument_parser(arg_list, desc=None):
    parser = argparse.ArgumentParser(description=desc)

    for arg in arg_list:
        parser.add_argument(arg[0], type=arg[1], default=arg[2], help=arg[3])

    return parser.parse_args()


# convert tuple or list of tuples to dict by set keys
def tuplelist_to_dict(tuplelist, num):
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


def remove_duplicate(list_):
    return list(set(list_))


def func_time(logger):
    def decorator(function):
        def wrapper(*args, **kwargs):
            start = time.time()
            resuls = function(*args, **kwargs)
            logger.info("Time {} is {}".format(function.__name__, time.time() - start))
            return resuls

        wrapper.__name__ = function.__name__
        return wrapper

    return decorator


def datetime_to_iso(dt):
    return dt.isoformat()


def sort_branches(branches):
    """Sort branch names by actuality

    Args:
        branches (list): list of branch names

    Returns:
        tuple: list of sorted branch names
    """
    # sort elements that starts with key in sort_order_keys
    sort_order_keys = (("s", False), ("p", True), ("c", True), ("t", True))
    res = []

    def _get_serial(x):
        # try to find number sequence from input string and return it as integer
        # or return input value length
        numbers = "0123456789"
        numbers_pos = [x.find(n) for n in numbers]
        if max(numbers_pos) == -1:
            return len(x)
        serial_ = ""
        first_num = min([x for x in numbers_pos if x != -1])
        for i in range(first_num, len(x)):
            if x[i] in numbers:
                serial_ += x[i]
            else:
                break
        return int(serial_)

    for sk in sort_order_keys:
        res += sorted(
            [x for x in branches if x.startswith(sk[0])],
            key=lambda k: _get_serial(k),
            reverse=sk[1],
        )

    res += sorted([_ for _ in branches if _ not in res], reverse=True)

    return tuple(res)


def get_nickname_from_packager(packager):
    email_match = re.compile("(<.+@?.+>)+")
    m = email_match.search(packager)
    if m is None:
        # return original string if no regex match found
        return packager
    email_ = m.group(1).strip().replace(" at ", "@")
    email_ = email_.lstrip("<")
    nickname = email_.split("@")[0]
    return nickname


def dp_flags_decode(dp_flag: int, dp_decode_table: list) -> List[str]:
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


def full_file_permissions(file_type, file_mode):
    res = ""
    types = {
        "file": "-",
        "directory": "d",
        "symlink": "l",
        "socket": "s",
        "block": "b",
        "char": "c",
        "fifo": "p"
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


def bytes2human(size: int) -> str:
    """Convert file size in bytes to human readable string representation."""
    for unit in ["", "K", "M", "G", "T", "P", "E"]:
        if abs(size) < 1024.0:
            return f"{size:3.1f} {unit}B"
        size /= 1024.0
    return f"{size:.1f} ZB"
