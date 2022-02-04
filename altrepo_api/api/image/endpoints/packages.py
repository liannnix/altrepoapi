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

from altrepo_api.api.base import APIWorker
from altrepo_api.api.misc import lut
from ..sql import sql
from altrepo_api.libs.conflict_filter import ConflictFilter


class CheckPackages(APIWorker):
    """Check packages from distribution image for consistency."""

    def __init__(self, connection, payload, **kwargs):
        self.conn = connection
        self.payload = payload
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        self.validation_results = []

        if self.payload["branch"] not in lut.known_branches:
            self.validation_results.append(
                f"unknown package set name : {self.payload['branch']}"
            )
            self.validation_results.append(
                f"allowed package set names are : {lut.known_branches}"
            )

        if self.validation_results != []:
            return False
        else:
            return True

    def post_regular(self):
        self.branch = self.payload["branch"]
        self.args = {"branch": self.branch}

        Package = namedtuple(
            "Package",
            [
                "hash",
                "name",
                "epoch",
                "version",
                "release",
                "arch",
                "disttag",
                "buildtime",
            ],
        )

        def pkg2ntuple(p: dict) -> Package:
            return Package(
                hash=int(p["pkg_hash"]),
                arch=p["pkg_arch"],
                name=p["pkg_name"],
                epoch=int(p["pkg_epoch"]),
                version=p["pkg_version"],
                release=p["pkg_release"],
                disttag=p["pkg_disttag"],
                buildtime=int(p["pkg_buildtime"]),
            )

        packages = [pkg2ntuple(p) for p in self.payload["packages"]]

        # create temporary table with input packages
        tmp_table = "_TmpInPkgs"
        self.conn.request_line = self.sql.create_tmp_table.format(
            tmp_table=tmp_table, columns=self.sql.tmp_table_columns,
        )
        status, response = self.conn.send_request()
        if status is False:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        self.conn.request_line = (
            self.sql.insert_into_tmp_table.format(tmp_table=tmp_table),
            (tuple(p) for p in packages),
        )
        status, response = self.conn.send_request()
        if status is False:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error

        pkgs_not_found = set()
        pkgs_not_in_db = set()
        pkgs_in_tasks = set()
        pkgs_tasks = list()
        # check if packages in DB for branch
        self.conn.request_line = self.sql.get_pkgs_not_in_branch.format(
            tmp_table=tmp_table, branch=self.branch
        )
        status, response = self.conn.send_request()
        if status is False:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        if not response:
            self._store_error(
                {"message": "No data found in database"},
                self.ll.ERROR,
                404,
            )
            return self.error
        pkgs_not_found = {x[0] for x in response if x[1] == 0}
        # get tasks for packages that are not in branch
        if pkgs_not_found:
            self.conn.request_line = self.sql.get_pkgs_tasks.format(
                hshs=tuple(pkgs_not_found)
            )
            status, response = self.conn.send_request()
            if status is False:
                self._store_sql_error(response, self.ll.ERROR, 500)
                return self.error

            PkgTask = namedtuple("PkgTask", ["hash", "taskid", "subtaskid"])
            pkgs_tasks = [PkgTask(*el) for el in response]
            pkgs_in_tasks = {p.hash for p in pkgs_tasks}

        pkgs_not_in_db = pkgs_not_found - pkgs_in_tasks

        # drop temporary table
        self.conn.request_line = self.sql.drop_tmp_table.format(tmp_table=tmp_table)
        status, response = self.conn.send_request()
        if status is False:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error

        # build result response
        res = {
            "request_args": self.args,
            "input_pakages": len(packages),
            "not_in_branch": len(pkgs_not_found),
            "found_in_tasks": len(pkgs_in_tasks),
            "not_found_in_db": len(pkgs_not_in_db),
        }

        res["packages_in_tasks"] = []
        for pkg in (p for p in packages if p.hash in pkgs_in_tasks):
            d = pkg._asdict()
            d["hash"] = str(d["hash"])
            for t in pkgs_tasks:
                if t.hash == pkg.hash:
                    d.update(
                        {
                            "task_id": t.taskid,
                            "subtask_id": t.subtaskid,
                        }
                    )
                    break
            res["packages_in_tasks"].append(d)

        res["packages_not_in_db"] = []
        for pkg in (p for p in packages if p.hash in pkgs_not_in_db):
            d = pkg._asdict()
            d["hash"] = str(d["hash"])
            res["packages_not_in_db"].append(d)

        return res, 200

    def post_sp(self):
        self.branch = self.payload["branch"]
        self.args = {"branch": self.branch}

        Package = namedtuple(
            "Package",
            [
                "hash",
                "name",
                "epoch",
                "version",
                "release",
                "disttag",
                "arch",
                "buildtime",
            ],
        )

        def pkg2ntuple(p: dict) -> Package:
            return Package(
                hash=int(p["pkg_hash"]),
                arch=p["pkg_arch"],
                name=p["pkg_name"],
                epoch=int(p["pkg_epoch"]),
                version=p["pkg_version"],
                release=p["pkg_release"],
                disttag=p["pkg_disttag"],
                buildtime=int(p["pkg_buildtime"]),
            )

        packages = [pkg2ntuple(p) for p in self.payload["packages"]]

        # create temporary table with input packages
        tmp_table = "_TmpInPkgs"
        self.conn.request_line = self.sql.create_tmp_table.format(
            tmp_table=tmp_table, columns=self.sql.tmp_table_columns
        )
        status, response = self.conn.send_request()
        if status is False:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        self.conn.request_line = (
            self.sql.insert_into_tmp_table.format(tmp_table=tmp_table),
            (tuple(p) for p in packages),
        )
        status, response = self.conn.send_request()
        if status is False:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error

        pkgs_in_branch = set()
        pkgs_not_found = set()
        pkgs_not_in_db = set()
        pkgs_in_tasks = set()

        # create temporary table with packages in DB for branch
        tmp_table2 = "_TmpPkgsInBranch"
        self.conn.request_line = self.sql.tmp_pkgs_in_branch.format(
            tmp_table=tmp_table2, tmp_table2=tmp_table, branch=self.branch
        )
        status, response = self.conn.send_request()
        if status is False:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error

        tmp_table3 = "_TmpPkgHshsByNEVR"
        self.conn.request_line = self.sql.tmp_pkgs_by_nevr.format(
            tmp_table=tmp_table3, tmp_table2=tmp_table, branch=self.branch
        )
        status, response = self.conn.send_request()
        if status is False:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error

        self.conn.request_line = self.sql.select_all_tmp_table.format(
            tmp_table=tmp_table2
        )
        status, response = self.conn.send_request()
        if status is False:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error

        packages_in_branch = [Package(*el) for el in response]

        # get input and branch packages matching
        _empty_p = Package(0, "", 0, "", "", "", "", 0)

        def key_nevrda(p: Package) -> tuple:
            return (p.name, p.epoch, p.version, p.release, p.disttag, p.arch)

        def key_nevra(p: Package) -> tuple:
            return (p.name, p.epoch, p.version, p.release, p.arch)

        # pkgs_compare -> dict(tuple, list(Package, Package, str))
        pkgs_compare: dict[tuple, list] = {}
        for p in packages:
            key = key_nevrda(p)
            pkgs_compare[key] = [p, _empty_p, "not found"]
        for p in packages_in_branch:
            key = key_nevrda(p)
            if key in pkgs_compare:
                pkgs_compare[key][1] = p
                pkgs_compare[key][2] = "branch"

        pkgs_in_branch = {p.hash for p, _, s in pkgs_compare.values() if s == "branch"}
        pkgs_not_found = {
            p.hash for p, _, s in pkgs_compare.values() if s == "not found"
        }

        # compare versions
        def compare_versions(p1: Package, p2: Package) -> int:
            # 0 : equal, 1 : v1 > v2, -1 : v1 < v2
            return ConflictFilter._compare_version(
                vv1=(p1.epoch, p1.version, p1.release, p1.disttag),
                vv2=(p2.epoch, p2.version, p2.release, p2.disttag)
            )
        # get not found packages without disttag
        # search packages in last branch state by NAME+ARCH
        V_CMP_NONE = 127
        pkgs_compare_ver: dict[tuple, list] = {}
        if pkgs_not_found:
            self.conn.request_line = self.sql.get_pkgs_last_branch_by_na.format(
                branch=self.branch,
                na=[(p[1], p[6]) for p in packages if p.hash in pkgs_not_found],
            )
            status, response = self.conn.send_request()
            if status is False:
                self._store_sql_error(response, self.ll.ERROR, 500)
                return self.error

            pkgs_nf_last = [Package(*el) for el in response]

            for p1 in (p for p in packages if p.hash in pkgs_not_found):
                key = key_nevrda(p1)
                # kp1 = key_nevra(p1)
                kp1 = (p1.name, p1.arch)
                pkgs_compare_ver[key] = [p1, _empty_p, V_CMP_NONE]
                for p2 in pkgs_nf_last:
                    # kp2 = key_nevra(p2)
                    kp2 = (p2.name, p2.arch)
                    if kp2 == kp1:
                        pkgs_compare_ver[key][1] = p2
                        pkgs_compare_ver[key][2] = compare_versions(p1, p2)
                        break

        # search not found packages in tasks
        if pkgs_not_found:
            self.conn.request_line = self.sql.truncate_tmp_table.format(
                tmp_table=tmp_table
            )
            status, response = self.conn.send_request()
            if status is False:
                self._store_sql_error(response, self.ll.ERROR, 500)
                return self.error

            self.conn.request_line = (
                self.sql.insert_into_tmp_table.format(tmp_table=tmp_table),
                (tuple(p) for p in packages if p.hash in pkgs_not_found),
            )
            status, response = self.conn.send_request()
            if status is False:
                self._store_sql_error(response, self.ll.ERROR, 500)
                return self.error

            self.conn.request_line = self.sql.get_pkgs_tasks_nevr.format(
                tmp_table=tmp_table
            )
            status, response = self.conn.send_request()
            if status is False:
                self._store_sql_error(response, self.ll.ERROR, 500)
                return self.error

            pkgs_tasks = [(tuple(el[1:3]), Package(*el[3:])) for el in response]
            # update pkgs_compare dictionary wit packages from tasks
            for t, p in pkgs_tasks:
                key = key_nevrda(p)
                if key in pkgs_compare:
                    pkgs_compare[key][1] = p
                    pkgs_compare[key][2] = f"task [{t[0]}.{t[1]}]"

            pkgs_in_tasks = {
                p.hash for p, _, s in pkgs_compare.values() if s.startswith("task")
            }
            pkgs_not_in_db = pkgs_not_found - pkgs_in_tasks

        # search packages in last branch state by NEVRA excluding disttag
        if pkgs_not_in_db:
            self.conn.request_line = self.sql.get_pkgs_last_branch.format(
                branch=self.branch,
                nevra=[(*p[1:5], p[6]) for p in packages if p.hash in pkgs_not_found],
            )
            status, response = self.conn.send_request()
            if status is False:
                self._store_sql_error(response, self.ll.ERROR, 500)
                return self.error

            for p in [Package(*el) for el in response]:
                kp = key_nevra(p)
                for pp, _, _ in pkgs_compare.values():
                    kpp = key_nevra(pp)
                    if pp.hash in pkgs_not_in_db and kpp == kp:
                        key = key_nevrda(pp)
                        if key in pkgs_compare:
                            pkgs_compare[key][1] = p
                            pkgs_compare[key][2] = "last branch"

        # drop temporary tables
        self.conn.request_line = self.sql.drop_tmp_table.format(tmp_table=tmp_table)
        status, response = self.conn.send_request()
        if status is False:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error

        self.conn.request_line = self.sql.drop_tmp_table.format(tmp_table=tmp_table2)
        status, response = self.conn.send_request()
        if status is False:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error

        self.conn.request_line = self.sql.drop_tmp_table.format(tmp_table=tmp_table3)
        status, response = self.conn.send_request()
        if status is False:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error

        # build result response
        ver_cmp_ = {
            -1: "older",
            0: "equal",
            1: "newer",
            V_CMP_NONE: "none"
        }
        res = []
        for p1, p2, s in pkgs_compare.values():
            ver_check_ = pkgs_compare_ver.get(key_nevrda(p1), None)
            if ver_check_ is None or ver_check_[1] == _empty_p:
                if s != "branch":
                    ver_check_ = ver_cmp_[V_CMP_NONE]
                else:
                    ver_check_ = ver_cmp_[0]
                branch_p_ = _empty_p
            else:
                branch_p_ = ver_check_[1]
                ver_check_ = ver_cmp_[ver_check_[2]]
            
            d = {
                "image": p1._asdict(),
                "database": p2._asdict(),
                "last_branch": branch_p_._asdict(),
                "found_in": s,
                "version_check": ver_check_
            }
            # convert hashes to strings
            d["image"]["hash"] = str(d["image"]["hash"])
            d["database"]["hash"] = str(d["database"]["hash"])
            d["last_branch"]["hash"] = str(d["last_branch"]["hash"])
            res.append(d)

        res = {
            "request_args": self.args,
            "input_pakages": len(packages),
            "in_branch": len(pkgs_in_branch),
            "not_in_branch": len(pkgs_not_found),
            "found_in_tasks": len(pkgs_in_tasks),
            "not_found_in_db": len(pkgs_not_in_db),
            "packages": res,
        }

        return res, 200
