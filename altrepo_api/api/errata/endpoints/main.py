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

from dataclasses import asdict, dataclass
from datetime import date, datetime

from altrepo_api.api.base import APIWorker

from ..parsers import errataid_type
from ..sql import sql


def errata_link(eid: str, etype: str) -> str:
    if etype == "bug":
        return f"https://bugzilla.altlinux.org/{eid}"
    elif etype == "vuln":
        if eid.startswith("BDU"):
            return f"https://bdu.fstec.ru/vul/{eid.removeprefix('BDU:')}"
        elif eid.startswith("CVE"):
            return f"https://nvd.nist.gov/vuln/detail/{eid.lower()}"
        elif eid.startswith("MFSA"):
            return f"https://www.mozilla.org/en-US/security/advisories/mfsa{eid.removeprefix('MFSA ')}"
    return f"https://errata.altlinux.org/{eid}"


@dataclass
class Errata:
    hash: str
    type: str
    source: str
    references: list[tuple[str, str]]
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


@dataclass
class Bug:
    id: int
    status: str
    resolution: str
    severity: str
    priority: str
    product: str
    version: str
    platform: str
    component: str
    assignee: str
    reporter: str
    summary: str
    last_changed: datetime
    assignee_full: str
    reporter_full: str
    url: str


@dataclass
class Vuln:
    id: str
    hash: str
    type: str
    summary: str
    score: float
    severity: str
    url: str
    references: list[tuple[str, str]]
    modified_date: datetime
    published_date: datetime
    body: str


@dataclass
class PackageUpdate(Errata):
    bugs: list[Bug]
    vulns: list[Vuln]


@dataclass
class BranchUpdate(Errata):
    pkg_updates: list[PackageUpdate]


@dataclass
class Reference:
    type: str
    id: str
    link: str = ""

    def __post_init__(self):
        self.link = errata_link(self.id, self.type)


class BatchInfo(APIWorker):
    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def check_params_post(self):
        self.validation_results = []
        self.input_arguments = []

        for elem in self.args["json_data"]["errata_ids"]:
            try:
                self.input_arguments.append(errataid_type(elem))
            except ValueError:
                self.validation_results.append(f"invalid errata id: {elem}")

        if self.validation_results != []:
            return False
        else:
            return True

    def post(self):
        errata_ids = self.args["json_data"]["errata_ids"]

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


class Packages(APIWorker):
    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def check_params_post(self):
        self.validation_results = []
        self.input_arguments = []

        for elem in self.args["json_data"]["errata_ids"]:
            try:
                self.input_arguments.append(errataid_type(elem))
            except ValueError:
                self.validation_results.append(f"invalid errata id: {elem}")
            if not elem.startswith("ALT-PU-"):
                self.validation_results.append(f"not a package update: {elem}")

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

        erratas: list[Errata] = []
        vulns: dict[str, Vuln] = {}
        bugs: dict[int, Bug] = {}

        for row in response:
            erratas.append(Errata(*row))
            refs = row[3]
            for etype, eid in refs:
                if etype == "vuln":
                    vulns[eid] = None
                elif etype == "bug":
                    bugs[int(eid)] = None

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
        for row in response:
            vulns[row[0]] = Vuln(*row)
            vulns[row[0]].references = [
                link[1] for link in vulns[row[0]].references
            ]

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
        for row in response:
            bugs[row[0]] = Bug(*row, errata_link(row[0], "bug"))

        result = []
        for errata in erratas:
            pu_bugs = [
                bugs[int(eid)]
                for etype, eid in errata.references
                if etype == "bug" and bugs[int(eid)]
            ]
            pu_vulns = [
                vulns[eid]
                for etype, eid in errata.references
                if etype == "vuln" and vulns[eid]
            ]
            result.append(
                asdict(
                    PackageUpdate(*asdict(errata).values(), pu_bugs, pu_vulns)
                )
            )

        return {"pkg_updates": result}, 200


class Branches(APIWorker):
    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def check_params_post(self):
        self.validation_results = []
        self.input_arguments = []

        for elem in self.args["json_data"]["errata_ids"]:
            try:
                self.input_arguments.append(errataid_type(elem))
            except ValueError:
                self.validation_results.append(f"invalid errata id: {elem}")
            if not elem.startswith("ALT-BU-"):
                self.validation_results.append(f"not a branch update: {elem}")

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

        erratas = set()
        for row in response:
            for _, eid in row[3]:
                erratas.add(eid)

        request = {"errata_ids": list(erratas)}
        subquery = Packages(self.conn, json_data=request).post()
        if subquery[1] != 200:
            return self.store_error({"message": "No data found in database"})

        erratas = {
            el["id"]: PackageUpdate(**el) for el in subquery[0]["pkg_updates"]
        }

        result = []
        for bu in response:
            pus_ids = {eid for _, eid in bu[3]}
            pus = []
            for pu_id, val in erratas.items():
                if pu_id in pus_ids:
                    pus.append(val)
            result.append(
                asdict(
                    BranchUpdate(**(asdict(Errata(*bu)) | {"pkg_updates": pus}))
                )
            )

        return {"branch_updates": result}, 200


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
