# ALTRepo API
# Copyright (C) 2021-2024  BaseALT Ltd

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

from collections import defaultdict
from typing import NamedTuple

from altrepo_api.utils import valid_task_id
from altrepo_api.api.base import APIWorker

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
        if not valid_task_id(self.task_id):
            return False
        response = self.send_sql_request(self.sql.check_task.format(id=self.task_id))
        if not self.sql_status:
            return False

        return response[0][0] != 0

    def get(self):
        class Package(NamedTuple):
            name: str
            epoch: int
            version: str
            release: str
            disttag: str
            buildtime: str
            arch: str

        response = self.send_sql_request(
            self.sql.get_last_task_info.format(task_id=self.task_id)
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {"Error": f"No data found in database for task '{self.task_id}'"}
            )

        result = defaultdict(list)
        result["id"] = self.task_id

        for index, field in enumerate(
            [
                "state",
                "dependencies",
                "testonly",
                "message",
                "changed",
                "try",
                "iter",
                "repo",
                "owner",
            ],
            1,
        ):
            result[field] = response[0][index]

        response = self.send_sql_request(
            self.sql.get_task_subtasks_packages_hashes.format(
                task_id=self.task_id, task_try=result["try"], task_iter=result["iter"]
            )
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {"Error": f"No data found in database for task '{self.task_id}'"}
            )

        subtasks = {
            source: (subtask, binaries) for subtask, source, binaries in response
        }

        response = self.send_sql_request(
            self.sql.get_task_arepo_packages_hashes.format(
                task_id=self.task_id, task_try=result["try"], task_iter=result["iter"]
            )
        )
        if not self.sql_status:
            return self.error

        arepos = [p[0] for p in response]

        hashes = arepos.copy()
        for source, (_, binaries) in subtasks.items():
            hashes.append(source)
            hashes.extend(binaries)

        _tmp_table = "tmp_pkgs_hashes"
        response = self.send_sql_request(
            self.sql.get_packages_by_hashes.format(tmp_table=_tmp_table),
            external_tables=[
                {
                    "name": _tmp_table,
                    "structure": [
                        ("pkg_hash", "UInt64"),
                    ],
                    "data": [{"pkg_hash": int(hash)} for hash in hashes],
                },
            ],
        )
        if not self.sql_status:
            return self.error

        packages_map = {r[0]: Package(*r[1:]) for r in response}

        packages = {
            (subtask, packages_map[srchash]): [
                packages_map[binhash]
                for binhash in binhashes
                if binhash in packages_map
            ]
            for srchash, (subtask, binhashes) in subtasks.items()
        }

        result["arepo"] = sorted(
            [packages_map[arepo]._asdict() for arepo in arepos],
            key=lambda el: el["name"],
        )

        result["subtasks"] = sorted(
            [
                {
                    "subtask": subtask,
                    "source": source._asdict() | {"disttag": binaries[0].disttag},
                    "binaries": sorted(
                        [binary._asdict() for binary in binaries],
                        key=lambda el: (el["name"], el["arch"]),
                    ),
                }
                for (subtask, source), binaries in packages.items()
            ],
            key=lambda el: el["subtask"],
        )
        result["length"] = len(result["subtasks"])

        return result, 200
