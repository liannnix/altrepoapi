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

from datetime import datetime
from collections import defaultdict
from typing import NamedTuple

from altrepo_api.api.base import APIWorker
from altrepo_api.utils import mmhash
from altrepo_api.api.misc import lut
from ..sql import sql


class TaskPackages(APIWorker):
    """
    Show source and binary packages from task.
    """

    def __init__(self, connection, id_, **kwargs) -> None:
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        self.task_id = id_
        super().__init__()

    def check_task_id(self):
        response = self.send_sql_request(self.sql.check_task.format(id=self.task_id))
        if not self.sql_status:
            return False

        return response[0][0] != 0

    def get(self):
        class Package(NamedTuple):
            srpm: str
            source: int
            pkg_name: str
            pkg_version: str
            pkg_release: str
            pkg_disttag: str
            pkg_buildtime: str
            pkg_arch: str
            pkg_packager_email: str

        response = self.send_sql_request(
            self.sql.get_task_last_try_iter.format(task_id=self.task_id)
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {"Error": f"No data found in database for task '{self.task_id}'"}
            )

        last_try = response[0][0]
        last_iter = response[0][1]

        archs = lut.default_archs + ["x86_64-i586", "src"]

        tplans_hashes = [
            mmhash(f"{self.task_id}{last_try}{last_iter}{arch}") for arch in archs
        ]

        response = self.send_sql_request(
            self.sql.get_task_packages.format(tplan_hshs=tplans_hashes)
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {"Error": f"No data found in database for task '{self.task_id}'"}
            )
        packages = [Package(*r) for r in response if r[-2] != "x86_64-i586"]
        arepo_packages = [Package(*r) for r in response if r[-2] == "x86_64-i586"]

        result = defaultdict(list)
        result["id"] = self.task_id
        result["task_packages"] = [
            package.pkg_name for package in packages if package.source
        ]
        result["length"] = len(result["task_packages"])

        grouped = defaultdict(list)
        for package in packages:
            grouped[package.srpm].append(package)

            arepo = next(
                (
                    arepo
                    for arepo in arepo_packages
                    if f"i586-{package.pkg_name}" == arepo.pkg_name
                ),
                None,
            )
            if arepo:
                grouped[package.srpm].append(arepo)

        for packages in grouped.values():
            srcpkg = [p for p in packages if p.source][0]
            disttag = [p.pkg_disttag for p in packages if not p.source][0]
            binaries_names = {p.pkg_name for p in packages if not p.source}
            archs = {p.pkg_arch for p in packages if not p.source}

            result["packages"].append(
                {
                    "sourcepkgname": srcpkg.pkg_name,
                    "packages": binaries_names,
                    "version": srcpkg.pkg_version,
                    "release": srcpkg.pkg_release,
                    "disttag": disttag,
                    "packager_email": srcpkg.pkg_packager_email,
                    "buildtime": datetime.fromtimestamp(srcpkg.pkg_buildtime),
                    "archs": archs,
                }
            )

        return result, 200
