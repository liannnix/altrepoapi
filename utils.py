import json
import time
import logging
import datetime
import argparse
import configparser
from collections import defaultdict
import mmh3
from urllib.parse import unquote
from dataclasses import dataclass

from settings import namespace

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
        format=u'%(levelname)-8s [%(asctime)s] %(message)s',
        level=logging.DEBUG,
        filename=namespace.LOG_FILE
    )
    logger = logging.getLogger(name)

    return logger


def exception_to_logger(exception):
    # return exception.args[0].split('\n')[0]
    return exception.args[0].split('\n')[0]


def read_config(config_file):
    config = configparser.ConfigParser(inline_comment_prefixes="#")

    if config.read(config_file):
        return config

    return False

def url_logging(logger, url):
    logger.info(unquote(url))

# return error message as json format
def json_str_error(error):
    return {'Error': error}

# build SQL error response
def build_sql_error_response(response, cls, code, debug):
    if debug:
        response['module'] = cls.__class__.__name__
        requestline = cls.conn.request_line
        if isinstance(requestline, tuple):
            response['sql_request'] = [_ for _ in requestline[0].split('\n') if len(_) > 0]
            # response['sql_payload'] = list(requestline[1])
        else:
            response['sql_request'] = [_ for _ in requestline.split('\n')]
    return response, code

def convert_to_dict(keys, values):
    res = {}

    for i in range(len(values)):
        res[i] = dict([(keys[j], values[i][j]) for j in range(len(values[i]))])
    
    return res


def convert_to_json(keys, values, sort=False):
    js = {}

    for i in range(len(values)):
        js[i] = dict([(keys[j], values[i][j])
                      for j in range(len(values[i]))])

        for key in js[i]:
            if key == 'date':
                js[i]['date'] = datetime.datetime.strftime(
                    js[i]['date'], '%Y-%m-%d %H:%M:%S'
                )

    return json.dumps(js, sort_keys=sort)


def join_tuples(tuple_list):
    return tuple([tuple_[0] for tuple_ in tuple_list])


def print_statusbar(message_list):
    types = {
        'i': "[INFO]",
        'w': "[WARNING]",
        'd': "[DEBUG]",
        'e': "[ERROR]",
    }

    for msg in message_list:
        print("[ALTREPO SERVER]{type_}: {msg}"
              "".format(type_=types[msg[1]], msg=msg[0]))


def make_argument_parser(arg_list, desc=None):
    parser = argparse.ArgumentParser(description=desc)

    for arg in arg_list:
        parser.add_argument(arg[0], type=arg[1], default=arg[2], help=arg[3])

    return parser.parse_args()


# convert tuple or list of tuples to dict by set keys
def tuplelist_to_dict(tuplelist, num):
    result_dict = defaultdict(list)
    for tuple_ in tuplelist:
        count = tuple_[1] if num == 1 else tuple_[1:num + 1]

        if isinstance(count, tuple):
            result_dict[tuple_[0]] += [elem for elem in count]
        elif isinstance(count, list):
            result_dict[tuple_[0]] += count
        else:
            result_dict[tuple_[0]].append(count)

    return result_dict


def remove_duplicate(list_):
    return list(set(list_))


def get_helper(helper):
    return json.dumps(helper, sort_keys=False)


def func_time(logger):
    def decorator(function):
        def wrapper(*args, **kwargs):
            start = time.time()
            resuls = function(*args, **kwargs)
            logger.info(
                "Time {} is {}".format(function.__name__, time.time() - start)
            )
            return resuls

        wrapper.__name__ = function.__name__
        return wrapper

    return decorator

def datetime_to_iso(dt):
    return dt.isoformat()
