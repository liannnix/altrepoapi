import mmh3
import json
import time
import logging
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
    logging.basicConfig(
        format=u"%(levelname)-8s [%(asctime)s] %(message)s",
        level=settings.LOG_LEVEL,
        filename=settings.LOG_FILE,
    )
    logger = logging.getLogger(name)

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
    res = [_ for _ in branches if _.startswith("s")]
    res += sorted(
        [_ for _ in branches if _.startswith("p")],
        key=lambda k: int(k[1:]),
        reverse=True,
    )
    res += sorted([_ for _ in branches if _.startswith("c")], reverse=True)
    res += sorted([_ for _ in branches if _.startswith("t")], reverse=True)
    res += sorted([_ for _ in branches if _ not in res], reverse=True)

    return tuple(res)
