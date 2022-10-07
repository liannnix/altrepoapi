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

import rpm
from collections import defaultdict
from dataclasses import dataclass

from altrepo_api.api.base import ConnectionProto
from altrepo_api.utils import get_logger, tuplelist_to_dict, remove_duplicate

from .exceptions import SqlRequestError

logger = get_logger(__name__)


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
        pbranch: str,
        parch: str,
        debug_sql: bool = False,
    ):
        self.conn = connection
        self.sql = ConflictFilterSQL()
        self.pbranch = pbranch
        self.parch = parch
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

    def _get_dict_conflict_provide(self, hshs):

        # get conflicts and provides by hash
        self.conn.request_line = (
            self.sql.get_dependencies,
            {"hshs": tuple(hshs), "branch": self.pbranch, "arch": self.parch},
        )
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response)
            raise SqlRequestError(self.error)

        hsh_dpt_dict = defaultdict(lambda: defaultdict(list))
        for hsh, *args in response:
            dptype = "conflict" if args[0] == "obsolete" else args[0]
            hsh_dpt_dict[hsh][dptype] += [tuple(args[1:])]

        self.conn.request_line = (self.sql.get_packages_info, {"hshs": tuple(hshs)})
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response)
            raise SqlRequestError(self.error)

        return hsh_dpt_dict, tuplelist_to_dict(response, 4)

    def _get_conflicts(self, dA, dB, hshA, hshB, hsh_evrd):
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
        conflicts = []
        for confl in dA["conflict"]:
            for provd in dB["provide"]:
                if confl[0] == provd[0]:
                    # add conflict in list if conflict without version
                    if confl[1] == "" or confl[2] == 0:
                        conflicts.append((hshA, hshB))
                    else:
                        # version of provide
                        vv1 = tuple(hsh_evrd[hshB])
                        # version of conflict
                        vv2 = self._split_version(confl[1])

                        # make compare versions
                        eq = self._compare_version(vv1, vv2)

                        flag = confl[2]

                        # check conflict version flag (>, <, =, >=, <=)
                        if (
                            (eq == -1 and flag & 1 << 1 != 0)
                            or (eq == 0 and flag & 1 << 3 != 0)
                            or (eq == 1 and flag & 1 << 2 != 0)
                        ):
                            conflicts.append((hshA, hshB))

        return conflicts

    def detect_conflict(self, confl_list: list[tuple[int, ...]]):
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
        # also (epoch, version, release, disttag)
        hsh_dpt_dict, hsh_evrd = self._get_dict_conflict_provide(uniq_hshs)

        conflicts = []
        for hshA, hshB in confl_list:
            # A - conflicts; B - provides
            conflA = self._get_conflicts(
                hsh_dpt_dict[hshA], hsh_dpt_dict[hshB], hshA, hshB, hsh_evrd
            )
            # A - provides; B - conflicts
            conflB = self._get_conflicts(
                hsh_dpt_dict[hshB], hsh_dpt_dict[hshA], hshB, hshA, hsh_evrd
            )

            conflicts += remove_duplicate(conflA + conflB)

        return conflicts

    @staticmethod
    def _split_version(vers):
        """
        Split version of package.

        Version of packages may be contains also epoch, release, dist tag.
        It method split the version and returns each item separately.

        :param vers: version of package (dpversion in datatbase)
        :return: `int`: epoch, `str`: version, `str`: release, `str`: disttag
        """
        # split for `-alt` and get epoch, version
        epoch_vers = vers.split("-alt")[0]
        vers = vers.replace(epoch_vers, "")
        epoch_vers = epoch_vers.split(":")
        # get release, disttag
        rel_dist = vers.split(":")
        rel_dist[0] = rel_dist[0].replace("-", "")

        # release check, if not, release is 0
        if len(epoch_vers) < 2:
            epoch = 0
            vers = epoch_vers[0]
        else:
            epoch = int(epoch_vers[0])
            vers = epoch_vers[1]

        # disttag check, if not (disttag = ''), disttag is None
        dist = None
        if len(rel_dist) < 2:
            if rel_dist[0] != "":
                rel = rel_dist[0]
            else:
                rel = None
        else:
            rel = rel_dist[0]
            dist = rel_dist[1]

        return epoch, vers, rel, dist

    @staticmethod
    def _compare_version(vv1, vv2):
        """
        Compare versions of packages.

        The method compares versions (epoch, version, release, disttag) using
        the rpm module.

        :param vv1: version of first package
        :param vv2: version of second package
        :return: `0` if versions are identical
                 `1` if the first version is larger
                 `-1` if the first version is less
        """
        v1 = rpm.hdr()  # type: ignore
        v2 = rpm.hdr()  # type: ignore

        v1[rpm.RPMTAG_EPOCH] = vv1[0]  # type: ignore
        v2[rpm.RPMTAG_EPOCH] = vv2[0]  # type: ignore

        v1[rpm.RPMTAG_VERSION] = vv1[1]  # type: ignore
        v2[rpm.RPMTAG_VERSION] = vv2[1]  # type: ignore
        if vv1[2]:
            v1[rpm.RPMTAG_RELEASE] = vv1[2]  # type: ignore
        if vv2[2]:
            v2[rpm.RPMTAG_RELEASE] = vv2[2]  # type: ignore

        # check disttag, if true, add it
        if vv1[3] != "" and vv2[3]:
            v1[rpm.RPMTAG_DISTTAG] = vv1[3]  # type: ignore
            v2[rpm.RPMTAG_DISTTAG] = vv2[3]  # type: ignore

        eq = rpm.versionCompare(v1, v2)  # type: ignore

        return eq
