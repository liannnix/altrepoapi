import sys
from collections import defaultdict
from gunicorn.app.wsgiapp import run

import utils
from settings import namespace as settings


def start():
    assert sys.version_info >= (3, 7), "Pyhton version 3.7 or newer is required!"

    launch_props = [
        ("DATABASE_HOST", str),
        ("DATABASE_NAME", str),
        ("TRY_CONNECTION_NUMBER", int),
        ("TRY_TIMEOUT", int),
        ("DATABASE_USER", str),
        ("DATABASE_PASS", str),
        ("DEFAULT_HOST", str),
        ("DEFAULT_PORT", int),
        ("WORKER_PROCESSES", str),
        ("WORKER_TIMEOUT", str),
        ("LOG_FILE", str),
    ]

    pars_args = [
        ("--host", str, None, "host to start application"),
        ("--port", int, None, "port to start application"),
        ("--dbhost", str, None, "database host"),
        ("--dbname", str, None, "database name"),
        ("--dbuser", str, None, "database user"),
        ("--dbpassword", str, None, "database password"),
        ("--config", str, settings.CONFIG_FILE, "path to db config file"),
        ("--prcs", str, None, "number of worker processes"),
        ("--timeout", str, None, "worker timeout"),
        ("--logs", str, None, "path to log files"),
    ]

    parser = utils.make_argument_parser(pars_args)

    config = utils.read_config(parser.config)

    if config:

        args_dict = defaultdict(dict)
        for section in config.sections():
            for option in config.options(section):
                args_dict[section.lower()][option] = config.get(section, option)

        params = {
            "database": [
                ("host", settings.DATABASE_HOST),
                ("name", settings.DATABASE_NAME),
                ("try_numbers", settings.TRY_CONNECTION_NUMBER),
                ("try_timeout", settings.TRY_TIMEOUT),
                ("user", settings.DATABASE_USER),
                ("password", settings.DATABASE_PASS),
            ],
            "application": [
                ("host", settings.DEFAULT_HOST),
                ("port", settings.DEFAULT_PORT),
                ("processes", settings.WORKER_PROCESSES),
                ("timeout", settings.WORKER_TIMEOUT),
            ],
            "other": [("logfiles", settings.LOG_FILE)],
        }

        val_list = []
        for section, items in params.items():
            for line in items:
                value = args_dict.get(section)
                val_list.append(value.get(line[0]) if value else line[1])

        for i, val in enumerate(val_list):
            if val:
                settings.__setattr__(
                    launch_props[i][0], launch_props[i][1](val)
                )

    parser_keys = [
        "dbhost",
        "dbname",
        "",
        "",
        "dbuser",
        "dbpassword",
        "host",
        "port",
        "prcs",
        "timeout"
        "logs",
    ]

    for i, parser_key in enumerate(parser_keys):
        if parser.__contains__(parser_key):
            pars_val = parser.__getattribute__(parser_key)

            if pars_val:
                settings.__setattr__(launch_props[i][0], launch_props[i][1](pars_val))

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
