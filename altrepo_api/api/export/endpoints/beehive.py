# ALTRepo API
# Copyright (C) 2021-2025  BaseALT Ltd

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
from typing import Any, NamedTuple

from altrepo_api.utils import datetime_to_iso
from altrepo_api.api.base import APIWorker
from altrepo_api.api.misc import lut
from ..sql import sql


class BeehiveStatus(NamedTuple):
    branch: str
    hash: int
    name: str
    epoch: int
    version: str
    release: str
    arch: str
    updated: datetime
    ftbfs_since: datetime


class BeehiveFTBFS(APIWorker):
    """Retrieves Beehive rebuild errors."""

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        self.validation_results = []

        branch = self.args["branch"]
        if branch not in lut.known_beehive_branches:
            self.validation_results.append(
                f"Unknown branch for Beehive: {branch}. Use one of {lut.known_beehive_branches}"
            )

        arch = self.args.get("arch")
        if arch is not None and arch not in lut.known_beehive_archs:
            self.validation_results.append(
                f"Unknown arch for Beehive: {arch}. Use one of {lut.known_beehive_archs}"
            )

        return self.validation_results == []

    def get(self):
        branch = self.args["branch"]
        _arch = self.args.get("arch")
        archs = (_arch,) if _arch else tuple(lut.known_beehive_archs)
        self.args["arch"] = archs

        response = self.send_sql_request(
            sql.get_beehive_errors_by_branch_and_arch.format(branch=branch, archs=archs)
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {"message": "No data not found in database", "args": self.args},
            )

        res: list[dict[str, Any]] = []

        for el in (BeehiveStatus(*r) for r in response):
            epoch_ = el.epoch
            if epoch_ == 0:
                epoch_version = el.version
            else:
                epoch_version = str(epoch_) + ":" + el.version

            url = "/".join(
                (
                    lut.beehive_base,
                    "logs",
                    "Sisyphus" if el.branch == "sisyphus" else el.branch,
                    el.arch,
                    "archive",
                    el.updated.strftime("%Y/%m%d"),
                    "error",
                    "-".join((el.name, epoch_version, el.release)),
                )
            )

            r = el._asdict()
            r["url"] = url
            r["hash"] = str(el.hash)
            r["updated"] = datetime_to_iso(el.updated)
            r["ftbfs_since"] = datetime_to_iso(el.ftbfs_since)
            res.append(r)

        return {"request_args": self.args, "length": len(res), "ftbfs": res}, 200
