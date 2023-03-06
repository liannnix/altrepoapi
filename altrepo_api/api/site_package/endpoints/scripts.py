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

from altrepo_api.utils import (
    tuplelist_to_dict,
    sort_branches,
)

from altrepo_api.api.base import APIWorker
from ..sql import sql


class BinaryPackageScripts(APIWorker):
    """Get scripts and versions of a binary package"""

    def __init__(self, connection, pkghash, **kwargs):
        self.conn = connection
        self.pkghash = pkghash
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def get(self):
        response = self.send_sql_request(
            self.sql.get_bin_pkg_scripts.format(pkghash=self.pkghash)
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {
                    "message": f"No information found in DB for package hash {self.pkghash}",
                    "args": self.pkghash,
                }
            )

        PkgScripts = namedtuple("PkgScripts", ["postin", "postun", "prein", "preun"])
        pkg_scripts = [PkgScripts(*el)._asdict() for el in response]

        # get package name and arch
        response = self.send_sql_request(
            self.sql.get_pkgs_name_and_arch.format(pkghash=self.pkghash)
        )
        if not self.sql_status:
            return self.error

        # get package versions
        pkg_versions = []
        pkg_name = response[0][0]  # type: ignore
        pkg_arch = response[0][1]  # type: ignore

        response = self.send_sql_request(
            self.sql.get_pkg_binary_versions.format(name=pkg_name, arch=pkg_arch)
        )
        if not self.sql_status:
            return self.error

        PkgVersions = namedtuple(
            "PkgVersions", ["branch", "version", "release", "pkghash"]
        )

        # sort package versions by branch
        pkg_branches = sort_branches([el[0] for el in response])  # type: ignore
        pkg_versions = tuplelist_to_dict(response, 3)  # type: ignore

        pkg_versions = [
            PkgVersions(*(b, *pkg_versions[b][-3:]))._asdict() for b in pkg_branches
        ]

        res = {
            "request_args": self.pkghash,
            "pkg_name": pkg_name,
            "pkg_arch": pkg_arch,
            "length": len(pkg_scripts),
            "scripts": pkg_scripts,
            "versions": pkg_versions,
        }
        return res, 200
