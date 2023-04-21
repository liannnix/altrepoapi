# ALTRepo API
# Copyright (C) 2021-2023  BaseALT Ltd

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
from typing import Any, Callable

from altrepo_api.utils import tuplelist_to_dict, sort_branches

from altrepo_api.api.base import APIWorker
from altrepo_api.api.misc import lut
from ..sql import sql


MAX_SEARCH_WORDS = 3
WEIGHT_MULT = 256


def predicate_all_match(key: str, names: list[str], value: Any) -> bool:
    return all(key.lower().find(n) != -1 for n in names)


def predicate_all_match_and_is_source(key: str, names: list[str], value: Any) -> bool:
    print(f"DBG: predicate : key : value : {key} : {value}")
    try:
        is_source = value[5] == 1
    except (ValueError, TypeError, IndexError):
        is_source = False

    return is_source and predicate_all_match(key, names, None)


def relevance_sort(
    pkgs_dict: dict[str, Any],
    pkg_names: list[str],
    predicate: Callable[[str, list[str], Any], bool] = predicate_all_match,
) -> list[tuple[Any, ...]]:
    """Sorts packages by some relevance. Values that matches by predicate function
    has precedence and those are not matched sorted in alphanumeric order."""

    # names = sorted(n.lower() for n in pkg_names)
    names = [n.lower() for n in pkg_names]

    def relevance_weight(key: str):
        # res = len(key) + 100 * key.find(names[0])
        res = len(key) + WEIGHT_MULT * sum(key.find(n) for n in names)
        print(f"DBG: key: weigth {key} : {res}")
        return res

    list_in = [k for k in pkgs_dict.keys() if predicate(k, names, pkgs_dict[k])]
    list_out = [k for k in pkgs_dict.keys() if not predicate(k, names, pkgs_dict[k])]

    list_in.sort(key=lambda x: relevance_weight(x))
    list_out.sort()

    print(f"DBG: list_in {list_in}")
    print(f"DBG: list_out {list_out}")

    return [(name, *pkgs_dict[name]) for name in (list_in + list_out)]


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

        name_like_clause = " AND ".join([f"pkg_name ILIKE '%{n}%'" for n in self.name])

        if self.args["branch"] is not None:
            self.branch = f"AND pkgset_name = '{self.args['branch']}'"

        if self.args["arch"] is None:
            self.arch = f"AND pkg_arch IN {(*lut.default_archs,)}"
            _sql = self.sql.get_find_packages_by_name.format(
                branch=self.branch,
                arch=self.arch,
                name_like=name_like_clause,
            )
        else:
            self.arch = f"AND pkg_arch IN {(self.args['arch'],)}"
            _sql = self.sql.get_find_packages_by_name_and_arch.format(
                branch=self.branch,
                arch=self.arch,
                name_like=name_like_clause,
            )

        response = self.send_sql_request(_sql)
        if not self.sql_status:
            return self.error

        res = []
        PkgMeta = namedtuple(
            "PkgMeta",
            ["branch", "version", "release", "pkghash", "deleted"],
            defaults=[False],  # 'deleted' default
        )

        if response:
            pkgs_sorted = relevance_sort(
                tuplelist_to_dict(response, 6),
                self.name,
                predicate_all_match_and_is_source,
            )

            for pkg in pkgs_sorted:
                res.append(
                    {
                        "name": pkg[0],
                        "buildtime": pkg[2],
                        "url": pkg[3],
                        "summary": pkg[4],
                        "category": pkg[5],
                        "versions": [PkgMeta(*el)._asdict() for el in pkg[1]],
                        "by_binary": True if pkg[6] == 0 else False,
                    }
                )

        # search in deleted packages
        response = self.send_sql_request(
            self.sql.get_find_deleted_packages_by_name.format(
                branch=self.branch, name_like=name_like_clause
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
                            "by_binary": False,
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
                    "message": f"Packages like '{' '.join(self.name)}' not found in database",
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

        name_like_clause = " AND ".join([f"pkg_name ILIKE '%{n}%'" for n in self.name])

        if self.args["branch"] is not None:
            self.branch = f"AND pkgset_name = '{self.args['branch']}'"

        response = self.send_sql_request(
            self.sql.get_fast_search_packages_by_name.format(
                branch=self.branch, name_like=name_like_clause
            )
        )
        if not self.sql_status:
            return self.error

        res = []

        if response:
            pkgs_sorted = relevance_sort(tuplelist_to_dict(response, 3), self.name)

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
                branch=self.branch, name_like=name_like_clause
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
                    "message": f"Packages like '{' '.join(self.name)}' not found in database",
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
