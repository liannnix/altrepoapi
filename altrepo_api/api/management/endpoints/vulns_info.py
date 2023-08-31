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
import datetime
import logging
from dataclasses import dataclass, field, asdict
from typing import Any, NamedTuple

from altrepo_api.api.base import APIWorker
from altrepo_api.api.management.sql import sql
from altrepo_api.api.parser import bdu_id_type, cve_id_type
from altrepo_api.utils import make_tmp_table_name


logger = logging.getLogger(__name__)


class Bug(NamedTuple):
    id: int
    summary: str = ""
    is_valid: bool = False


@dataclass
class VulnerabilityInfo:
    id: str
    hash: str = ""
    type: str = ""
    summary: str = ""
    score: float = 0.0
    severity: str = ""
    url: str = ""
    modified_date: datetime = datetime.datetime.fromtimestamp(0)
    published_date: datetime = datetime.datetime.fromtimestamp(0)
    body: dict[str, Any] = field(default_factory=dict)
    refs_type: list[str] = field(default_factory=list)
    refs_link: list[str] = field(default_factory=list)
    is_valid: bool = False
    related_vulns: list[str] = field(default_factory=list)

    def __post_init__(self):
        parsed = None

        try:
            parsed = json.loads(self.json)  # type: ignore
        except Exception:
            logger.debug(f"Failed to parse vulnerability JSON for {self.id}")
            pass

        if parsed is not None:
            self.json = parsed

    def asdict(self) -> dict[str, Any]:
        res = asdict(self)

        del res["refs_type"]
        del res["refs_link"]
        res["refs"] = [r for r in self.refs_link]

        return res


class VulnsInfo(APIWorker):
    """
    Find vulnerability information.
    """

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        self.cve_ids: set[str] = set()
        self.bdu_ids: set[str] = set()
        self.bug_ids: set[int] = set()
        super().__init__()

    def check_params_post(self):
        try:
            vuln_ids: list[str] = self.args["json_data"]["vuln_ids"]
        except (TypeError, KeyError):
            self.validation_results.append("Payload data parsing error")
            return False

        for vuln_id in vuln_ids:
            try:
                if vuln_id.startswith("BDU:"):
                    self.bdu_ids.add(bdu_id_type(vuln_id))
                elif vuln_id.startswith("CVE-"):
                    self.cve_ids.add(cve_id_type(vuln_id))
                elif vuln_id.isdigit():
                    self.bug_ids.add(int(vuln_id))
                else:
                    self.validation_results.append(f"invalid vuln id: {vuln_id}")
                    break
            except ValueError:
                self.validation_results.append(f"invalid vuln id: {vuln_id}")
                break

        if self.validation_results != []:
            return False

        return True

    def post(self):
        bugs: dict[str, dict[str, Any]] = {}
        vulns_found: dict[str, VulnerabilityInfo] = {}
        # get a list of found bugs in Bugzilla
        if self.bug_ids:
            tmp_table = make_tmp_table_name("bz_ids")
            response = self.send_sql_request(
                self.sql.get_bugs_by_ids.format(tmp_table=tmp_table),
                external_tables=[
                    {
                        "name": tmp_table,
                        "structure": [("bz_id", "UInt32")],
                        "data": [{"bz_id": bz_id} for bz_id in self.bug_ids],
                    },
                ],
            )
            if not self.sql_status:
                return self.error
            bugs = {row[0]: Bug(*row, is_valid=True)._asdict() for row in response}

        if self.cve_ids:
            # get CVE info
            response = self.send_sql_request(
                self.sql.get_vuln_info_by_ids.format(tmp_table=tuple(self.cve_ids))
            )
            if not self.sql_status:
                return self.error

            if response:
                vulns_found = {
                    el[0]: VulnerabilityInfo(*el, is_valid=True) for el in response
                }

                # get BDU id's from CVE
                response = self.send_sql_request(
                    self.sql.get_related_vulns_for_cve.format(
                        tmp_table=tuple(vulns_found.keys())
                    )
                )
                if not self.sql_status:
                    return self.error

                for bdu in response:
                    bdu = VulnerabilityInfo(*bdu, is_valid=True)
                    for idx, ref_type in enumerate(bdu.refs_type):
                        if ref_type == "CVE":
                            vulns_found[bdu.refs_link[idx]].related_vulns.append(bdu.id)
                    vulns_found[bdu.id] = bdu
                    if bdu.id in self.bdu_ids:
                        self.bdu_ids.remove(bdu.id)

        if self.bdu_ids:
            # get BDU info
            response = self.send_sql_request(
                self.sql.get_vuln_info_by_ids.format(tmp_table=tuple(self.bdu_ids))
            )
            if not self.sql_status:
                return self.error

            if response:
                cve_ids = []
                for bdu in response:
                    bdu = VulnerabilityInfo(*bdu, is_valid=True)
                    for idx, ref_type in enumerate(bdu.refs_type):
                        if ref_type == "CVE":
                            cve_ids.append(bdu.refs_link[idx])
                            bdu.related_vulns.append(bdu.refs_link[idx])
                    vulns_found[bdu.id] = bdu

                # get CVE id's from BDU
                response = self.send_sql_request(
                    self.sql.get_vuln_info_by_ids.format(tmp_table=tuple(cve_ids))
                )
                if not self.sql_status:
                    return self.error
                if response:
                    vulns_found = {
                        **vulns_found,
                        **{
                            el[0]: VulnerabilityInfo(*el, is_valid=True)
                            for el in response
                        },
                    }

        vulns = [asdict(el) for el in vulns_found.values()]
        # add invalids CVEs to the resulting list of vulnerabilities
        for cve in self.cve_ids:
            if cve not in vulns_found.keys():
                vulns.insert(0, asdict(VulnerabilityInfo(id=cve, type="CVE")))

        if not vulns and not bugs:
            return self.store_error(
                {
                    "message": f"No data info found in DB "
                    f"for {self.args['json_data']['vuln_ids']}"
                }
            )

        # BDUs and Bugzilla vulnerabilities not found in the DB
        not_found_vulns: list[str] = [
            bdu for bdu in self.bdu_ids if bdu not in vulns_found.keys()
        ]
        not_found_vulns += [bug for bug in self.bug_ids if bug not in bugs.keys()]

        res = {
            "bugs": list(bugs.values()),
            "vulns": vulns,
            "not_found": not_found_vulns,
        }

        return res, 200
