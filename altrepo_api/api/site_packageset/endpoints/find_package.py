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
from typing import Any

from altrepo_api.utils import tuplelist_to_dict, sort_branches

from altrepo_api.api.base import APIWorker
from altrepo_api.api.misc import lut
from ..sql import sql


def relevance_sort(pkgs_dict: dict[str, Any], pkg_name: str) -> list[tuple]:
    """Dumb sorting for package names by relevance."""

    def relevance_weight(instr, substr):
        return len(instr) + 100 * instr.find(substr)

    l_in = []
    l_out = []

    for k in pkgs_dict.keys():
        if k.lower().find(pkg_name.lower()) == -1:
            l_out.append(k)
        else:
            l_in.append(k)

    l_in.sort(key=lambda x: relevance_weight(x.lower(), pkg_name.lower()))
    l_out.sort()

    return [(name, *pkgs_dict[name]) for name in (l_in + l_out)]


class PackagesetFindPackages(APIWorker):
    """Finds packages in given package set by name relevance."""

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        return True

    def get(self):
        self.name = self.args["name"]
        self.arch = ""
        self.branch = ""

        if self.args["branch"] is not None:
            self.branch = f"AND pkgset_name = '{self.args['branch']}'"
        if self.args["arch"] is not None:
            self.arch = f"AND pkg_arch IN {(self.args['arch'],)}"
        else:
            self.arch = f"AND pkg_arch IN {(*lut.default_archs,)}"

        response = self.send_sql_request(
            self.sql.get_find_packages_by_name.format(
                branch=self.branch, name=self.name, arch=self.arch
            )
        )
        if not self.sql_status:
            return self.error

        res = []
        PkgMeta = namedtuple(
            "PkgMeta",
            ["branch", "version", "release", "pkghash", "deleted"],
            defaults=[False],  # 'deleted' default
        )

        if response:
            pkgs_sorted = relevance_sort(tuplelist_to_dict(response, 5), self.name)

            for pkg in pkgs_sorted:
                res.append(
                    {
                        "name": pkg[0],
                        "buildtime": pkg[2],
                        "url": pkg[3],
                        "summary": pkg[4],
                        "category": pkg[5],
                        "versions": [PkgMeta(*el)._asdict() for el in pkg[1]],
                    }
                )

        # search in deleted packages
        response = self.send_sql_request(
            self.sql.get_find_deleted_packages_by_name.format(
                branch=self.branch, name=self.name
            )
        )
        if not self.sql_status:
            return self.error

        if response:
            pkgs_sorted = relevance_sort(tuplelist_to_dict(response, 5), self.name)

            src_pkgs_found = {p["name"] for p in res}

            for pkg in pkgs_sorted:
                if pkg[0] not in src_pkgs_found:
                    # add packages found as deleted if not overlapping with already found
                    res.append(
                        {
                            "name": pkg[0],
                            "buildtime": pkg[2],
                            "url": pkg[3],
                            "summary": pkg[4],
                            "category": pkg[5],
                            "versions": [PkgMeta(*el, True)._asdict() for el in pkg[1]],  # type: ignore
                        }
                    )
                else:
                    # update already found packages with deleted one
                    for r in res:
                        if r["name"] == pkg[0]:
                            r["versions"] += [PkgMeta(*el, True)._asdict() for el in pkg[1]]  # type: ignore
                            break

        if not res:
            return self.store_error(
                {
                    "message": f"Packages like '{self.name}' not found in database",
                    "args": self.args,
                }
            )

        res = {"request_args": self.args, "length": len(res), "packages": res}
        return res, 200


class FastPackagesSearchLookup(APIWorker):
    """Fast packages search lookup by name"""

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        return True

    def get(self):
        self.name = self.args["name"]
        self.branch = ""
        if self.args["branch"] is not None:
            self.branch = f"AND pkgset_name = '{self.args['branch']}'"

        response = self.send_sql_request(
            self.sql.get_fast_search_packages_by_name.format(
                branch=self.branch, name=self.name
            )
        )
        if not self.sql_status:
            return self.error

        res = []

        if response:
            pkgs_sorted = relevance_sort(tuplelist_to_dict(response, 3), self.name)  # type: ignore

            for pkg in pkgs_sorted:
                if pkg[1] == 1:
                    sourcepackage = "source"
                else:
                    sourcepackage = "binary"
                res.append(
                    {
                        "name": pkg[0],
                        "sourcepackage": sourcepackage,
                        "branches": sort_branches(pkg[2]),
                    }
                )

        # search for deleted packages
        response = self.send_sql_request(
            self.sql.get_fast_search_deleted_packages_by_name.format(
                branch=self.branch, name=self.name
            )
        )
        if not self.sql_status:
            return self.error

        if response:
            pkgs_sorted = relevance_sort(tuplelist_to_dict(response, 5), self.name)
            src_pkgs_found = {p["name"] for p in res if p["sourcepackage"] == "source"}

            for pkg in pkgs_sorted:
                if pkg[0] not in src_pkgs_found:
                    if pkg[1] == 1:
                        sourcepackage = "source"
                    else:
                        sourcepackage = "binary"
                    res.append(
                        {
                            "name": pkg[0],
                            "sourcepackage": sourcepackage,
                            "branches": sort_branches(pkg[2]),
                        }
                    )
                else:
                    for r in res:
                        if r["name"] == pkg[0]:
                            r["branches"] = list(
                                set(r["branches"] + sort_branches(pkg[2]))
                            )
                        break

        if not res:
            return self.store_error(
                {
                    "message": f"Packages like '{self.name}' not found in database",
                    "args": self.args,
                }
            )

        res = {"request_args": self.args, "length": len(res), "packages": res}
        return res, 200


class PackagesetPkghashByNVR(APIWorker):
    """Finds package hash in given package set by name, version and release."""

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        return True

    def get(self):
        self.name = self.args["name"]
        self.branch = self.args["branch"]
        self.version = self.args["version"]
        self.release = self.args["release"]

        response = self.send_sql_request(
            self.sql.get_pkghash_by_BVR.format(
                branch=self.branch,
                name=self.name,
                version=self.version,
                release=self.release,
            )
        )
        if not self.sql_status:
            return self.error
        if not response or response[0][0] == 0:  # type: ignore
            return self.store_error(
                {
                    "message": (
                        f"Package '{self.name}-{self.version}-{self.release}' "
                        f"not found in database for branch {self.branch}"
                    ),
                    "args": self.args,
                }
            )

        return {"request_args": self.args, "pkghash": str(response[0][0])}, 200  # type: ignore
