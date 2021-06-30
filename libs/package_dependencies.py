from dataclasses import dataclass
from collections import namedtuple

from utils import get_logger, logger_level as ll
from utils import tuplelist_to_dict

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
    groupUniqArray(pkg_hash),
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

    def __init__(self, connection, packages, branch, archs, debug_):
        self.conn = connection
        self.sql = PackageDependenciesSQL()
        self.packages = packages
        self.branch = branch
        self.archs = archs
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

    def _get_package_dep_set(self, pkgs=None, first=False):

        self.conn.request_line = self.sql.get_srchsh_for_binary.format(
            pkgs=pkgs,
            branch=self.branch,
            archs=tuple(self.archs)
        )
        status, response = self.conn.send_request()
        if status is False:
            self._store_sql_error(response, ll.ERROR)
            raise SqlRequestError(self.error)

        tmp_list = []
        for key, val in response:
            if first:
                self.dep_dict[key] = val
                tmp_list += list(set(val) - set(tmp_list))
            else:
                for pkg, hshs in self.dep_dict.items():
                    hshs_set = set(hshs)
                    if key in hshs_set:
                        uniq_hshs = list(set(val) - hshs_set)
                        self.dep_dict[pkg] += uniq_hshs
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
            ((hsh,) for hsh in tmp_list)
        )
        status, response = self.conn.send_request()
        if status is False:
            self._store_sql_error(response, ll.ERROR)
            raise SqlRequestError(self.error)

        if not tmp_list:
            return self.dep_dict

        return self._get_package_dep_set(
            pkgs=self.sql.select_from_tmp_table.format(tmp_table=self._tmp_table)
        )

    def build_result(self):
        hsh_dict = self._get_package_dep_set(self.packages, first=True)
        tmp_table = 'all_hshs'
        self.conn.request_line = self.sql.create_tmp_table.format(
            tmp_table=tmp_table
        )
        status, response = self.conn.send_request()
        if status is False:
            self._store_sql_error(response, ll.ERROR)
            raise SqlRequestError(self.error)

        hsh_list = tuple(hsh_dict.keys()) + tuple([hsh for val in hsh_dict.values() for hsh in val])

        self.conn.request_line = (
            self.sql.insert_to_tmp_table.format(tmp_tbl=tmp_table),
            ((hsh,) for hsh in hsh_list)
        )
        status, response = self.conn.send_request()
        if status is False:
            self._store_sql_error(response, ll.ERROR)
            raise SqlRequestError(self.error)
        # get information for all packages in hsh_dict (keys and values) 
        self.conn.request_line = self.sql.get_meta_by_hshs.format(
            tmp_table=tmp_table
        )
        status, response = self.conn.send_request()
        if status is False:
            self._store_sql_error(response, ll.ERROR)
            raise SqlRequestError(self.error)

        dict_info = dict([(tuple(r[0]), r[1:]) for r in response])

        PkgInfo = namedtuple('PkgInfo', ['name', 'version', 'release', 'epoch', 'archs'])
        result_list = []

        for pkg, hshs in hsh_dict.items():
            counter = 0
            control_list = set()
            pkg_req_list = []

            for hsh in hshs:
                dict_info_key = [k for k in dict_info.keys() if hsh in k][0]
                dict_info_val = dict_info[dict_info_key]
                control_list_el = tuple(dict_info_val[:4])

                if control_list_el not in control_list:
                    control_list.add(control_list_el)
                    pkg_req_list.append(PkgInfo(*dict_info_val)._asdict())
                    counter += 1
            
            pkg_key = [k for k in dict_info.keys() if pkg in k][0]
            result_list.append({
                'package': dict_info[pkg_key][0],
                'length': counter,
                'depends': sorted(pkg_req_list, key=lambda val: val['name'])
            })

        return result_list
