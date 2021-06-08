import time
from clickhouse_driver import Client, errors
from utils import get_logger, exception_to_logger, json_str_error, print_statusbar, func_time
from paths import namespace

logger = get_logger(__name__)


class DBConnection:
    def __init__(self, clickhouse_host=None, clickhouse_name=None, dbuser=None,
                 dbpass=None, db_query=None):

        self.db_query = db_query

        self.clickhouse_client = Client(
            host=clickhouse_host, database=clickhouse_name, user=dbuser,
            password=dbpass
        )

        try_conn = self._connection_test()
        if try_conn:
            raise try_conn

        self.connection_status = False

    def make_connection(self):
        try:
            self.clickhouse_client.connection.connect()
        except Exception as error:
            logger.error(error)
            return False

        self.connection_status = True

        return True

    def _connection_test(self):
        try:
            self.clickhouse_client.connection.connect()
        except errors.Error as error:
            logger.error(exception_to_logger(error))
            return "Error of database connection."

        self.clickhouse_client.disconnect()
        return None

    def send_request(self, trace=False):
        response_status = False

        try:
            if isinstance(self.db_query, tuple):
                response = self.clickhouse_client.execute(
                    self.db_query[0], self.db_query[1]
                )
            else:
                response = self.clickhouse_client.execute(self.db_query)
            response_status = True
        except Exception as error:
            logger.error(exception_to_logger(error))
            response = json_str_error("Error in sql query!")
            if trace:
                print_statusbar([(error, 'd',)])

        return response_status, response

    def disconnect(self):
        self.clickhouse_client.disconnect()
        self.connection_status = False


class Connection:

    def __init__(self, request_line=None):
        self.request_line = request_line
        self.db_connection = DBConnection(
            namespace.DATABASE_HOST, namespace.DATABASE_NAME,
            namespace.DATABASE_USER, namespace.DATABASE_PASS
        )

    @func_time(logger)
    def send_request(self, trace=False):
        rl = self.request_line
        if isinstance(rl, tuple):
            rl = rl[0]

        if bool(rl) is False:
            return False, 'SQL query not found in query manager.'

        status = self.db_connection.connection_status
        if not status:
            for try_ in range(namespace.TRY_CONNECTION_NUMBER):
                logger.debug(
                    'Attempt to connect to the database #{}'.format(try_)
                )

                status = self.db_connection.make_connection()
                if status:
                    break

                time.sleep(namespace.TRY_TIMEOUT)

        if status:
            self.db_connection.db_query = self.request_line
            return self.db_connection.send_request(trace)
        else:
            return False, 'Database connection error.'

    def drop_connection(self):
        if self.db_connection:
            self.db_connection.disconnect()
            logger.debug('Connection closed.')