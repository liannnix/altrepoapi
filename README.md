# ALTRepo API

ALTRepo API is a REST API for the repository database of ALT
distribution. ALTRepo API allows users to get the necessary information 
regards to the repository by GET requests.

API documentation is available through Swagger web-interface.

# License

GNU AGPLv3

# Dependencies

* python3-module-flask-restx
* python3-module-flask
* python3-module-clickhouse-driver
* python3-module-mmh3
* python3-module-rpm
* python3-module-gunicorn

# Starting application

API could be started using `altrepo-api` binary to run application 
with Gunicorn server.

## Configuration file

Path to default configuration file is `/etc/altrepo-api/api.conf`.

Configuration file usually contains next sections:

    [DATABASE]
    HOST = 10.0.0.1        # database host
    NAME = database_name   # database name
    TRY_NUMBERS = 5        # number of connection attempts
    TRY_TIMEOUT = 5        # attempts timeout
    USER = test            # database user
    PASSWORD = test        # database password

    [APPLICATION]           # Used when API run with Gunicorn
    HOST = 127.0.0.1        # application host
    PORT = 5000             # port
    PROCESSES = 0           # number of worker processes, 0 - AUTO
    TIMEOUT = 30            # worker timeout in seconds

    [OTHER]
    ADMIN_USER = admin                              # API authorized user login
    ADMIN_PASSWORD = password_SHA512                # API authorized user password SHA512 hash
    LOGFILE = /var/log/altrepo_api/altrepo_api.log  # path to logfile
    LOG_LEVEL = 3           # 0 : critical, 1 : error, 2 : warning, 3 : info, 4 : debug
    SQL_DEBUG = false       # print detailed SQL requests
    LOG_TO_FILE = true      # log to file
    LOG_TO_SYSLOG = false   # log to syslog

Configuration file could be provided by command line argument or
environment variable (`ALTREPO_API_CONFIG`) or default value (`/etc/altrepo_api/api.conf`)
from `settings.py` in order of priority:

    Command line argument -> environment variable -> default.

## Starting application

API configuration could be provided by command line argument 
or through environment variable `ALTREPO_API_CONFIG`.
If not provided the default API configuration file (`/etc/altrepo-api/api.conf`) is used.

When installed from RPM package ALTRepo API could be started as follows:

    altrepo-api /path/to/config.file

    ALTREPO_API_CONFIG=/path/to/config.file altrepo-api

    altrepo-api [-h, --help]

For development purpose API could be started from cloned Git repository as follows:

    python3 -m altrepo_api /path/to/config.file

## Deploy ALTRepo API for production purpose

AltrepoAPI application could be deployed with 

Systemd unit files and Nginx configuration files examples could be found in
`/usr/share/doc/altrepo-api-%version%/examples` directory.

Provided configuration examples for:
1. Guncorn (application server) + Nginx (proxy server)
2. uWSGI (application server) + Nginx (proxy server)

You could use another application servers (Nginx Unit, Apache2 + mod_wsgi etc.)
using `/usr/share/altrepo-api/wsgi.py` as application entry point.

# Run API with Docker container

You can build and run ALTRepo API Docker container using alt:p10 base image.

## Build Docker image

Building ALTRepo API container is quite easy with docker-compose:

    [root@host]# docker-compose build

Or you could just start the container with

    [root@host]# docker-compose up

and it will be built automatically.

## Docker container persistent data

Containered API uses two volumes to store persistent data for configuration and log files. By default it is located at: 

    /var/lib/docker/volumes/altrepo-api_config/_data/api.conf
    /var/lib/docker/volumes/altrepo-api_log/_data/api.log

## Run Docker container

At first run the container to initialize persistent volumes:

    [root@host]# docker-compose up

API will fail due to default configuration has to be filled with actual settings. AT least you should configure DB connection and API administrator password.
Stop the container with command:

    [root@host]# docker-compose down

Then edit API config file in

    [root@host]# nano /var/lib/docker/volumes/altrepo-api_config/_data/api.conf

with actual DB connection data, administartor password and logging options. You could change Gunicorn workers number here as well (`0` value means auto).

When ready run the container as daemon with:

    [root@host]# docker-compose up -d

Now ALTrepo API should be available at `http://{your.docker.host.ip}:5000/api`

## Stop Docker container

To stop the running API container, use:

    [root@host]# docker-compose down
### Usefull Docker commands

    docker-compose logs [-f]    # view container stdout
    docker ps [-a]              # list containers
    docker image [ls | rm]      # list or remove images
    docker volume [ls | rm]     # list or remove volumes
    docker image prune          # cleaun up images ! use it with care !
    docker volume prune         # cleaun up images ! use it with care !

# Examples of query

The response from the server is returned as json data, for their 
formatted mapping is convenient to use jq utility.

All API endpoints and response models are described in Swagger web-interface at `http://{altrepo.api.address:port}/api/`

(* replace API address or domain name and port in accordance to web-server configuration)
