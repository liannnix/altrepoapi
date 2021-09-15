# ALTRepo API (clickhouse database)

ALTRepo API is a REST API for the repository database of ALT
distribution. ALTRepo API allows users to get the necessary information 
regards to the repository by GET requests.

API documentation is available by Swagger web-interface at

http://altrepo.api.address/api/

## Dependencies

* python3-module-flask-restx
* python3-module-flask
* python3-module-clickhouse-driver
* python3-module-rpm
* python3-module-gunicorn

## Components

* altrepo-server - executable file to run the project
* app.py - main module of application
* settings.py - provides configuration namespace for application
* run_app.py - module for launching the application and processing
input parameters
* utils.py - contains auxiliary functions used in application
* database/* - contains modules and data structures to work with ClickHouse database
* api/* - contains all API logic split by routes and endpoints
* libs/* - special modules for working with mathematics, data,
data structure are used in the application
* tests/* - test related files

## Starting application

Best to use a bunch of nginx and gunicorn servers to run.

First step

	git clone `git_project_repository`
	git checkout `last_tag_or_master`

### Simple example of nginx setting

Make file

	/etc/nginx/sites-available.d/altrepo_server.conf 

..with next content

    server {
        listen PORT;
        server_name HOST;
        
        root /PATH/TO/altrepo_server;
        
        access_log /PATH/TO/logs/access.log;
        error_log /PATH/TO/logs/error.log;
        
        location / {
            proxy_set_header X-Forward-For $proxy_add_x_forwarded_for;
            proxy_set_header Host $http_host;
            proxy_redirect off;
            if (!-f $request_filename) {
                proxy_pass http://127.0.0.1:8000;
                break;
            }
        }
    }

..make symlink

	/etc/nginx/sites-enabled.d/altrepo_server.conf
	->
	/etc/nginx/sites-available.d/altrepo_server.conf

### Configuration file of database

Path to default configuration file

	/etc/altrepo_server/dbconfig.conf

but you can override it use option --config for launch application.

Configuration file usually contains next sections

	[DataBase]
    HOST = 10.0.0.1        # database host
    NAME = database_name   # database name
    TRY_NUMBERS = 5        # number of connection attempts
    TRY_TIMEOUT = 5        # attempts timeout
    USER = test            # database user
    PASSWORD = test        # database password

    [Application]
    HOST = 127.0.0.1    # application host
    PORT = 5000         # port
    PROCESSES = 1       # number of worker processes
    TIMEOUT = 30        # worker timeout in seconds

    [Other]
    LOGFILE = /home/`user`/altrepo_server.log   # path to logfile
    ADMIN_USER = admin                      # API authorized user login
    ADMIN_PASSWORD = admin_password_sha512  # API authorized user password SHA512 hash

Also you can set launch options use keys. For more information use -h.

### Starting application

For start application using module run_app. For set app configuration
can be using config file ex.:

    ./altrepo-server --config /path/to/config/file.conf

or use launch keys, for more information

    ./altrepo-server --help

Start application from git catalog

    ./altrepo-server `allow_options` &

..after the application will run in the background.

## Examples of query

The response from the server is returned as json data, for their 
formatted mapping is convenient to use jq utility.

All API endpoints and response models are described in Swagger web-interface at: 
    http://localhost/api/ 
(* replace API address or domain name in accordance to web-server configuration)
