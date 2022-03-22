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

from collections import namedtuple

from altrepo_api.utils import sort_branches, datetime_to_iso

from altrepo_api.api.base import APIWorker
from altrepo_api.api.misc import lut
from ..sql import sql


class AllPackagesets(APIWorker):
    """Retrieves package sets names and source packages count."""

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def get(self):
        self.conn.request_line = self.sql.get_all_pkgset_names
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        if not response:
            self._store_error(
                {"message": f"No data not found in database", "args": self.args},
                self.ll.INFO,
                404,
            )
            return self.error

        pkg_branches = sort_branches(response[0][0])
        res = [{"branch": b, "count": 0} for b in pkg_branches]

        res = {"length": len(res), "branches": res}
        return res, 200

    def get_with_pkgs_count(self):
        self.conn.request_line = self.sql.get_all_pkgset_names_with_pkg_count
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        if not response:
            self._store_error(
                {"message": f"No data not found in database", "args": self.args},
                self.ll.INFO,
                404,
            )
            return self.error

        PkgCount = namedtuple("PkgCount", ["branch", "count"])
        # sort package counts by branch
        pkg_branches = sort_branches([el[0] for el in response])
        pkg_counts = {el[0]: el[1] for el in response}
        res = [PkgCount(*(b, pkg_counts[b]))._asdict() for b in pkg_branches]

        res = {"length": len(res), "branches": res}
        return res, 200

    def get_summary(self):
        self.conn.request_line = self.sql.get_all_pkgsets_with_src_cnt_by_bin_archs
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        if not response:
            self._store_error(
                {"message": f"No data not found in database", "args": self.args},
                self.ll.INFO,
                404,
            )
            return self.error

        PkgCount = namedtuple("PkgCount", ["branch", "arch", "count"])
        counts = {}

        for cnt in [PkgCount(*el) for el in response]:
            if cnt.branch not in counts:
                counts[cnt.branch] = []
            counts[cnt.branch].append({"arch": cnt.arch, "count": cnt.count})

        # sort package counts by branch
        res = [
            {"branch": br, "packages_count": counts[br]}
            for br in sort_branches(counts.keys())
        ]

        res = {"length": len(res), "branches": res}
        return res, 200

    def get_summary_status(self):
        self.conn.request_line = self.sql.get_all_pkgsets_with_src_cnt_by_bin_archs
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        if not response:
            self._store_error(
                {"message": f"No data not found in database", "args": self.args},
                self.ll.INFO,
                404,
            )
            return self.error

        PkgCount = namedtuple("PkgCount", ["branch", "arch", "count"])
        counts = {}

        for cnt in [PkgCount(*el) for el in response]:
            if cnt.branch not in counts:
                counts[cnt.branch] = []
            counts[cnt.branch].append({"arch": cnt.arch, "count": cnt.count})

        # get pkgset status info
        self.conn.request_line = self.sql.get_pkgset_status

        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error

        if not response:
            self._store_error(
                {"message": f"No data not found in database", "args": self.args},
                self.ll.INFO,
                404,
            )
            return self.error

        RepositoryStatusInfo = namedtuple(
            "RepositoryStatusInfo",
            [
                "start_date",
                "end_date",
                "show",
                "description_ru",
                "description_en",
            ],
        )

        statuses = {el[0]: RepositoryStatusInfo(*el[1:])._asdict() for el in response}

        # check if branch has active images
        self.conn.request_line = self.sql.get_branch_has_active_images

        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error

        branch_images = set()
        if response:
            branch_images = {el[0] for el in response}

        # format dates
        for k, el in statuses.items():
            el["start_date"] = datetime_to_iso(el["start_date"])
            el["end_date"] = datetime_to_iso(el["end_date"])
            # add flag if has active images
            el["has_images"] = 1 if k in branch_images else 0
        # sort statuses by branch
        statuses = [
            {"branch": br, **statuses[br]} for br in sort_branches(statuses.keys())
        ]

        # sort package counts by branch
        res = [
            {"branch": br, "packages_count": counts[br]}
            for br in sort_branches(counts.keys())
        ]

        res = {"length": len(res), "branches": res, "status": statuses}
        return res, 200


class PkgsetCategoriesCount(APIWorker):
    """Retrieves package sets categories and packages count."""

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        return True

    def get(self):
        self.branch = self.args["branch"]
        self.pkg_type = self.args["package_type"]

        pkg_type_to_sql = {"source": (1,), "binary": (0,), "all": (1, 0)}
        sourcef = pkg_type_to_sql[self.pkg_type]

        self.conn.request_line = self.sql.get_pkgset_groups_count.format(
            branch=self.branch, sourcef=sourcef
        )
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        if not response:
            self._store_error(
                {"message": f"No data not found in database", "args": self.args},
                self.ll.INFO,
                404,
            )
            return self.error

        res = [{"category": el[0], "count": el[1]} for el in response]

        res = {"request_args": self.args, "length": len(res), "categories": res}
        return res, 200


class AllPackagesetArchs(APIWorker):
    """Retrieves package sets architectures and source packages count by binary packages architecture."""

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        return True

    def get(self):
        self.branch = self.args["branch"]
        self.conn.request_line = self.sql.get_all_bin_pkg_archs.format(
            branch=self.branch
        )
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        if not response:
            self._store_error(
                {"message": f"No data not found in database", "args": self.args},
                self.ll.INFO,
                404,
            )
            return self.error

        archs = sorted([x for x in response[0][0] if x not in ("x86_64-i586",)])
        res = [x for x in archs if x.startswith("x")]
        res += [x for x in archs if x.startswith("i")]
        res += [x for x in archs if x.startswith("n")]
        res += sorted([x for x in archs if x not in res])

        res = [{"arch": x, "count": 0} for x in res]

        res = {"length": len(res), "archs": res}
        return res, 200

    def get_with_src_count(self):
        self.branch = self.args["branch"]
        self.conn.request_line = self.sql.get_all_src_cnt_by_bin_archs.format(
            branch=self.branch
        )
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        if not response:
            self._store_error(
                {"message": f"No data not found in database", "args": self.args},
                self.ll.INFO,
                404,
            )
            return self.error

        archs = sorted(
            [(*el,) for el in response], key=lambda val: val[1], reverse=True
        )
        res = [{"arch": x[0], "count": x[1]} for x in archs]

        res = {"length": len(res), "archs": res}
        return res, 200
