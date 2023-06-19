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

from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from typing import Union

from altrepo_api.api.base import APIWorker

from altrepo_api.api.parser import errata_id_type
from ..sql import sql


@dataclass
class Reference:
    type: str
    id: str


@dataclass
class Errata:
    hash: str
    type: str
    source: str
    references: list[Reference]
    id: str
    pkg_hash: str
    pkg_name: str
    pkg_version: str
    pkg_release: str
    pkgset_name: str
    pkgset_date: date
    task_id: int
    subtask_id: int
    task_state: str
    task_changed: date


DATETIME_NEVER = datetime.fromtimestamp(0)


@dataclass
class Vulnerability:
    id: str
    type: str
    hash: str = ""
    summary: str = ""
    score: float = 0.0
    severity: str = ""
    url: str = ""
    references: list[str] = field(default_factory=list)
    modified_date: datetime = DATETIME_NEVER
    published_date: datetime = DATETIME_NEVER
    body: str = ""
    is_valid: bool = False


def empty_vuln(vuln_id: str) -> Vulnerability:
    vuln_type = ""
    if vuln_id.startswith("CVE-"):
        vuln_type = "CVE"
    elif vuln_id.startswith("BDU:"):
        vuln_type = "BDU"
    return Vulnerability(id=vuln_id, type=vuln_type)


@dataclass
class Bug:
    id: int
    summary: str = ""
    is_valid: bool = False


@dataclass
class PackageUpdate(Errata):
    bugs: list[Bug]
    vulns: list[Vulnerability]


@dataclass
class BranchUpdate(Errata):
    packages_updates: list[PackageUpdate]


class Erratas(APIWorker):
    def __init__(self, connection):
        self.conn = connection
        self.sql = sql
        super().__init__()

    def fetch(self, errata_ids: list[str]) -> Union[list[Errata], None]:
        self.status = False
        _tmp_table = "tmp_errata_ids"
        response = self.send_sql_request(
            self.sql.get_errata_history_by_ids.format(
                tmp_table=_tmp_table,
            ),
            external_tables=[
                {
                    "name": _tmp_table,
                    "structure": [("errata_id", "String")],
                    "data": [
                        {"errata_id": errata_id} for errata_id in errata_ids
                    ],
                },
            ],
        )
        if not self.sql_status:
            return None
        if not response:
            _ = self.store_error({"message": "No erratas found in database"})
            return None

        self.status = True
        return [
            Errata(
                *row[:3],
                [Reference(*el) for el in row[3]],
                *row[4:],
            )
            for row in response
        ]


class PackagesUpdates(APIWorker):
    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def check_params(self):
        self.validation_results = []
        self.input_arguments = []

        for elem in self.args["json_data"]["errata_ids"]:
            try:
                self.input_arguments.append(errata_id_type(elem))
            except ValueError:
                self.validation_results.append(f"invalid errata id: {elem}")
                break
            if not elem.startswith("ALT-PU-"):
                self.validation_results.append(f"not a package update: {elem}")
                break

        if self.validation_results != []:
            return False
        else:
            return True

    def fetch(self, errata_ids: list[str]) -> Union[list[PackageUpdate], None]:
        self.status = False

        e = Erratas(self.conn)
        erratas = e.fetch(errata_ids)
        if not e.status:
            return None
        if erratas is None:
            _ = self.store_error(
                {"message": f"No errata data found for {errata_ids}"}
            )
            return None

        vulns: dict[str, Vulnerability] = {}
        bugs: dict[int, Bug] = {}

        for errata in erratas:
            vulns.update(
                {
                    v.id: v
                    for v in (
                        empty_vuln(ref.id)
                        for ref in errata.references
                        if ref.type == "vuln"
                    )
                }
            )
            bugs.update(
                {
                    b.id: b
                    for b in (
                        Bug(id=int(ref.id))
                        for ref in errata.references
                        if ref.type == "bug"
                    )
                }
            )

        _tmp_table = "tmp_vuln_ids"
        response = self.send_sql_request(
            self.sql.get_vulns_by_ids.format(
                tmp_table=_tmp_table,
            ),
            external_tables=[
                {
                    "name": _tmp_table,
                    "structure": [("vuln_id", "String")],
                    "data": [{"vuln_id": vuln_id} for vuln_id in vulns],
                },
            ],
        )
        if not self.sql_status:
            return None

        vulns.update(
            {
                vuln.id: vuln
                for vuln in (
                    Vulnerability(*row, is_valid=True) for row in response
                )
            }
        )

        _tmp_table = "tmp_bz_ids"
        response = self.send_sql_request(
            self.sql.get_bugs_by_ids.format(
                tmp_table=_tmp_table,
            ),
            external_tables=[
                {
                    "name": _tmp_table,
                    "structure": [("bz_id", "UInt32")],
                    "data": [{"bz_id": bz_id} for bz_id in bugs],
                },
            ],
        )
        if not self.sql_status:
            return None

        bugs.update(
            {
                bug.id: bug
                for bug in (Bug(*row, is_valid=True) for row in response)
            }
        )

        result = []
        for errata in erratas:
            pu_bugs = [
                bugs[int(ref.id)]
                for ref in errata.references
                if ref.type == "bug"
            ]
            pu_vulns = [
                vulns[ref.id] for ref in errata.references if ref.type == "vuln"
            ]
            result.append(
                PackageUpdate(
                    *asdict(errata).values(), bugs=pu_bugs, vulns=pu_vulns
                )
            )

        self.status = True
        return result

    def post(self):
        errata_ids = self.args["json_data"]["errata_ids"]

        packages_updates = self.fetch(errata_ids)
        if not self.status:
            return self.error
        if packages_updates is None:
            return self.store_error(
                {"message": f"No errata data found for {errata_ids}"}
            )

        return {"packages_updates": [asdict(p) for p in packages_updates]}, 200


class BranchesUpdates(APIWorker):
    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def check_params(self):
        self.validation_results = []
        self.input_arguments = []

        for elem in self.args["json_data"]["errata_ids"]:
            try:
                self.input_arguments.append(errata_id_type(elem))
            except ValueError:
                self.validation_results.append(f"invalid errata id: {elem}")
                break
            if not elem.startswith("ALT-BU-"):
                self.validation_results.append(f"not a branch update: {elem}")
                break

        if self.validation_results != []:
            return False
        else:
            return True

    def post(self):
        errata_ids = self.args["json_data"]["errata_ids"]

        _tmp_table = "tmp_vuln_ids"
        response = self.send_sql_request(
            self.sql.get_errata_history_by_ids.format(
                tmp_table=_tmp_table,
            ),
            external_tables=[
                {
                    "name": _tmp_table,
                    "structure": [("errata_id", "String")],
                    "data": [
                        {"errata_id": errata_id} for errata_id in errata_ids
                    ],
                },
            ],
        )
        if not response:
            return self.store_error({"message": "No data found in database"})

        packages_updates_ids = set()
        for row in response:
            for _, eid in row[3]:
                packages_updates_ids.add(eid)

        p = PackagesUpdates(self.conn)
        packages_updates = p.fetch(packages_updates_ids)
        if not p.status:
            return p.error
        if packages_updates is None:
            return p.store_error(
                {"message": f"No errata data found for {packages_updates_ids}"}
            )

        packages_updates_index = {
            package_update.id: package_update
            for package_update in packages_updates
        }

        branches_updates = []
        for row in response:
            packages_updates_ids = {errata_id for _, errata_id in row[3]}
            errata = asdict(Errata(*row))
            branch_update = BranchUpdate(
                **errata,
                packages_updates=[
                    asdict(packages_updates_index[package_update_id])
                    for package_update_id in packages_updates_ids
                ],
            )
            branches_updates.append(branch_update)

        return {"branches_updates": branches_updates}, 200


class Search(APIWorker):
    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def get(self):
        branch = self.args.get("branch")
        vuln_id = self.args.get("errata_id")
        package_name = self.args.get("package_name")

        conds = []

        if branch:
            conds.append(f"pkgset_name = '{branch}'")
        if vuln_id:
            conds.append(
                f"arrayExists(x -> (x ILIKE '%{vuln_id}%'), eh_references.link)"
            )
        if package_name:
            conds.append(f"pkg_name LIKE '%{package_name}%'")

        cond = ""
        if conds:
            cond = "WHERE " + " AND ".join(conds)

        response = self.send_sql_request(
            self.sql.search_errata.format(cond=cond)
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {"message": "No data not found in database", "args": self.args}
            )

        return {
            "erratas": [
                asdict(
                    Errata(
                        *row[:3],
                        [asdict(Reference(*el)) for el in row[3]],
                        *row[4:],
                    )
                )
                for row in response
            ]
        }, 200
