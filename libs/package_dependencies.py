from dataclasses import dataclass

from utils import get_logger, logger_level as ll
from utils import tuplelist_to_dict, remove_duplicate

from .exceptions import SqlRequestError

logger = get_logger(__name__)


@dataclass(frozen=True)
class PackageDependenciesSQL:
    create_tmp_table = """
CREATE TEMPORARY TABLE {tmp_table} (hsh UInt64)
"""

    select_from_tmp_table = """
SELECT hsh FROM {tmp_table}
"""

    drop_tmp_table = """
DROP TABLE IF EXISTS {tmp_table}
"""

    insert_to_tmp_table = """
INSERT INTO {tmp_tbl} (hsh) VALUES
"""

    get_srchsh_for_binary = """
SELECT DISTINCT
    srchsh,
    groupUniqArray(pkg_hash)
FROM
(
    SELECT
        pkg_hash AS srchsh,
        dp_name
    FROM Depends_buffer
    WHERE pkg_hash IN
    (
        {pkgs}
    )
        AND dp_type = 'require'
) AS sourceDep
INNER JOIN
(
    SELECT
        pkg_hash,
        dp_name
    FROM last_depends
    WHERE dp_type = 'provide'
        AND pkgset_name = '{branch}'
        AND pkg_sourcepackage = 0
        AND pkg_arch IN ({archs})
) AS binaryDeps USING dp_name
GROUP BY srchsh
"""

    get_meta_by_hshs = """
SELECT
    pkg_hash,
    pkg_name,
    pkg_version,
    pkg_release,
    pkg_epoch,
    groupUniqArray(pkg_arch)
FROM Packages_buffer
WHERE pkg_hash IN
(
    SELECT hsh
    FROM {tmp_table}
)
GROUP BY
(
    pkg_hash,
    pkg_name,
    pkg_version,
    pkg_release,
    pkg_epoch
)
"""


class PackageDependencies:
    """
    In this class, temporary tables are used to record the results of queries.
    This is necessary in order to avoid exceeding the limit count of input data
    in clickhouse database.
    """

    def __init__(self, connection, pbranch, debug_):
        self.conn = connection
        self.sql = PackageDependenciesSQL()
        self.pbranch = pbranch
        self.static_archs = ['x86_64', 'noarch']
        self.dep_dict = {}
        self._tmp_table = 'tmp_pkg_hshs'
        self.DEBUG = debug_

    def _log_error(self, severity):
        if severity == ll.CRITICAL:
            logger.critical(self.error)
        elif severity == ll.ERROR:
            logger.error(self.error)
        elif severity == ll.WARNING:
            logger.warning(self.error)
        elif severity == ll.INFO:
            logger.info(self.error)
        else:
            logger.debug(self.error)

    def _store_sql_error(self, message, severity):
        def build_sql_error(message):
            response = {'message': message}
            if self.DEBUG:
                response['module'] = self.__class__.__name__
                requestline = self.conn.request_line
                if isinstance(requestline, tuple):
                    response['sql_request'] = [_ for _ in requestline[0].split('\n') if len(_) > 0]
                else:
                    response['sql_request'] = [_ for _ in requestline.split('\n')]
            return response
        self.error = build_sql_error(message)
        self.status = False
        self._log_error(severity)

    def _store_error(self, message, severity):
        self.error = {'message': message}
        self.status = False
        self._log_error(severity)

    def get_package_dep_set(self, pkgs=None, first=False):

        self.conn.request_line = self.sql.get_srchsh_for_binary.format(
            pkgs=pkgs,
            branch=self.pbranch,
            archs=tuple(self.static_archs)
        )
        status, response = self.conn.send_request()
        if status is False:
            self._store_sql_error(response, ll.ERROR)
            raise SqlRequestError(self.error)

        # FIXME: needed optimization
        tmp_list = []
        for key, val in response:
            if first:
                self.dep_dict[key] = val
                tmp_list = val
                # tmp_list += [hsh for hsh in val if hsh not in tmp_list]
            else:
                for pkg, hshs in self.dep_dict.items():
                    hshs_set = set(hshs)
                    if key in hshs_set:
                        uniq_hshs = list(set(val) - hshs_set)
                        # uniq_hshs = [l for l in val if l not in hshs]
                        self.dep_dict[pkg] += uniq_hshs
                        # self.dep_dict[pkg] += tuple(uniq_hshs)
                        tmp_list += uniq_hshs

        self.conn.request_line = self.sql.drop_tmp_table.format(tmp_table=self._tmp_table)
        status, response = self.conn.send_request()
        if status is False:
            self._store_sql_error(response, ll.ERROR)
            raise SqlRequestError(self.error)

        self.conn.request_line = self.sql.create_tmp_table.format(tmp_table=self._tmp_table)
        status, response = self.conn.send_request()
        if status is False:
            self._store_sql_error(response, ll.ERROR)
            raise SqlRequestError(self.error)

        self.conn.request_line = (
            self.sql.insert_to_tmp_table.format(tmp_tbl=self._tmp_table),
            tuple([(hsh,) for hsh in tmp_list])
        )
        status, response = self.conn.send_request()
        if status is False:
            self._store_sql_error(response, ll.ERROR)
            raise SqlRequestError(self.error)

        if not tmp_list:
            return self.dep_dict

        return self.get_package_dep_set(
            pkgs=self.sql.select_from_tmp_table.format(tmp_table=self._tmp_table)
        )

    # @staticmethod
    def make_result_dict(self, hsh_list, hsh_dict):
        tmp_table = 'all_hshs'
        self.conn.request_line = self.sql.create_tmp_table.format(
            tmp_table=tmp_table
        )
        status, response = self.conn.send_request()
        if status is False:
            self._store_sql_error(response, ll.ERROR)
            raise SqlRequestError(self.error)

        self.conn.request_line = (
            self.sql.insert_to_tmp_table.format(tmp_tbl=tmp_table),
            tuple([(hsh,) for hsh in hsh_list])
        )
        status, response = self.conn.send_request()
        if status is False:
            self._store_sql_error(response, ll.ERROR)
            raise SqlRequestError(self.error)

        self.conn.request_line = self.sql.get_meta_by_hshs.format(
            tmp_table=tmp_table
        )
        status, response = self.conn.send_request()
        if status is False:
            self._store_sql_error(response, ll.ERROR)
            raise SqlRequestError(self.error)

        dict_info = tuplelist_to_dict(response, 5)

        # FIXME: needed optimization (archs)
        fields = ['name', 'version', 'release', 'epoch', 'archs']
        result_dict = {}
        for pkg, hshs in hsh_dict.items():

            counter = 0
            control_list, pkg_req_dict = [], {}
            for hsh in hshs:
                first = dict_info[hsh]

                archs = ()
                for hh in hshs:
                    second = dict_info[hh]

                    if first[:3] == second[:3]:
                        archs += tuple(second[4])

                dict_info[hsh][4] = tuple(set(archs))

                if dict_info[hsh] not in control_list:
                    control_list.append(dict_info[hsh])

                    pkg_info_dict = {}
                    for i in range(len(fields)):
                        pkg_info_dict[fields[i]] = dict_info[hsh][i]

                    pkg_req_dict[counter] = pkg_info_dict
                    counter += 1

            result_dict[dict_info[pkg][0]] = pkg_req_dict

        return result_dict
