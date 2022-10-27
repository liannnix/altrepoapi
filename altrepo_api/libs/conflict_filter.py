# ALTRepo API
# Copyright (C) 2021-2022  BaseALT Ltd

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

from collections import defaultdict, namedtuple
from dataclasses import dataclass

from altrepo_api.api.base import ConnectionProto
from altrepo_api.utils import get_logger, remove_duplicate

from .librpm_functions import check_dependency_overlap
from .exceptions import SqlRequestError

logger = get_logger(__name__)

# type aliases
DepsDictElType = dict[str, list[tuple[str, str, int]]]
DepsDictType = dict[int, DepsDictElType]
HashPair = tuple[int, int]


@dataclass(frozen=True)
class ConflictFilterSQL:
    get_dependencies = """
SELECT DISTINCT
    pkg_hash,
    dp_type,
    dp_name,
    dp_version,
    dp_flag
FROM Depends
WHERE pkg_hash IN %(hshs)s
    AND dp_type IN ('conflict', 'provide', 'obsolete')
"""

    get_packages_info = """
SELECT
    pkg_hash,
    pkg_epoch,
    pkg_version,
    pkg_release,
    pkg_disttag
FROM Packages
WHERE pkg_hash IN %(hshs)s
"""


class ConflictFilter:
    """
    Class for conflicts filter.

    Class contains method which finds conflicts and obsoletes between two
    packages and its auxiliary methods.

    :param connection: database connection instance
    :param pbranch: name of package repository
    :param parch: packages archs
    :param debug_: SQL debug flag
    """

    def __init__(
        self,
        connection: ConnectionProto,
        debug_sql: bool = False,
    ):
        self.conn = connection
        self.sql = ConflictFilterSQL()
        self.status = False
        self._debug = debug_sql

    def _store_sql_error(self, message):
        self.error = {"message": message}

        if self._debug:
            self.error["module"] = self.__class__.__name__
            requestline = self.conn.request_line

            if isinstance(requestline, tuple):
                self.error["sql_request"] = [
                    line for line in requestline[0].split("\n") if len(line) > 0
                ]
            else:
                self.error["sql_request"] = [line for line in requestline.split("\n")]

        logger.error(self.error)

    def _get_dict_conflict_provide(self, hshs: list[int]) -> DepsDictType:

        # get conflicts and provides by hash
        self.conn.request_line = (
            self.sql.get_dependencies,
            {"hshs": tuple(hshs)},
        )
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response)
            raise SqlRequestError(self.error)

        hsh_dpt_dict = defaultdict(lambda: defaultdict(list))
        for hsh, *deps in response:
            dptype = "conflict" if deps[0] == "obsolete" else deps[0]
            hsh_dpt_dict[hsh][dptype] += [tuple(deps[1:])]

        return hsh_dpt_dict  # type: ignore

    @staticmethod
    def _get_conflicts(
        dA: DepsDictElType, dB: DepsDictElType, hshA: int, hshB: int
    ) -> list[HashPair]:
        """
        Finds conflicts between two packages.

        Method of find conflicts between two packages uses conflicts of one
        and provides of the second package.

        :param dA: dict conflicts/provides package A
        :param dB: dict conflicts/provides package B
        :param hshA: hash package A
        :param hshB: hash package B
        :return: `list` of `tuple` (package hash, conflict hash) for package A
        """
        conflicts: list[HashPair] = []

        DependencyTuple = namedtuple("DependencyTuple", ["name", "version", "flags"])

        for confl in dA["conflict"]:
            C = DependencyTuple(*confl)
            for provd in dB["provide"]:
                P = DependencyTuple(*provd)
                if C.name == P.name and check_dependency_overlap(*P, *C):
                    conflicts.append((hshA, hshB))

        return conflicts

    def detect_conflict(self, confl_list: list[HashPair]) -> list[HashPair]:
        """
        Main public class method.

        List of package tuples that conflict with the given package. Return
        join list for package A and package B.

        :param confl_list: list of tuples with package hashes
        :return: `list` of `tuple` (package hash, conflict hash) for
        input list
        """

        # get unique package hashes
        uniq_hshs = list({hsh for confl in confl_list for hsh in confl})

        # get conflicts and provides for every unique package
        hsh_dpt_dict = self._get_dict_conflict_provide(uniq_hshs)

        conflicts: list[HashPair] = []

        for hshA, hshB in confl_list:
            # A - conflicts; B - provides
            conflA = self._get_conflicts(
                hsh_dpt_dict[hshA], hsh_dpt_dict[hshB], hshA, hshB
            )
            # A - provides; B - conflicts
            conflB = self._get_conflicts(
                hsh_dpt_dict[hshB], hsh_dpt_dict[hshA], hshB, hshA
            )

            conflicts += remove_duplicate(conflA + conflB)

        return conflicts
