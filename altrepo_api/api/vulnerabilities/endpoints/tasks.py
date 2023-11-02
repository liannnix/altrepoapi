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

from typing import NamedTuple

from altrepo_api.api.base import APIWorker
from altrepo_api.api.misc import lut

from .common import BDU_ID_PREFIX, CVE_ID_PREFIX
from ..sql import sql


class TaskInfo(NamedTuple):
    task_id: int
    task_state: str
    dependencies: list[str]
    task_testonly: int
    task_message: str
    task_changed: str
    task_try: int
    task_iter: int
    task_repo: str
    task_owner: str


class TaskErrataInfo(NamedTuple):
    pkghash: int
    subtask: int
    pkg_name: str
    pkg_version: str
    pkg_release: str
    branch: str
    errata_id: str
    vuln_ids: list[str]
    vuln_types: list[str]
    errata_link: str = ""
    vulnerabilities: list[dict[str, str]] = []


class TaskVulns(NamedTuple):
    id: str
    type: str
    link: str


class TaskVulnerabilities(APIWorker):
    """
    Get a list of fixed CVEs from task.
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
        # get fixed vulnerabilities in the task
        vulnerabilities = []
        response = self.send_sql_request(
            self.sql.get_task_cve_from_erratas.format(
                task_id=self.task_id,
            )
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {
                    "Error": f"No fixed vulnerabilities found in database for task '{self.task_id}'"
                }
            )

        for el in response:
            errata_info = TaskErrataInfo(*el)
            vulns = []
            for v_id, v_type in zip(errata_info.vuln_ids, errata_info.vuln_types):
                # build vulnerability link
                if v_id.startswith(CVE_ID_PREFIX):
                    url = f"{lut.nvd_cve_base}/{v_id}"
                elif v_id.startswith(BDU_ID_PREFIX):
                    url = f"{lut.fstec_bdu_base}/{v_id.split(':')[-1]}"
                elif v_type == "bug":
                    url = f"{lut.bugzilla_base}/{v_id}"
                else:
                    url = ""
                vulns.append(TaskVulns(v_id, v_type, url)._asdict())

            # build errata link to errata.altlinux.org
            errata_link = f"{lut.errata_base}/{errata_info.errata_id}"
            errata_info = errata_info._replace(
                vulnerabilities=vulns, errata_link=errata_link
            )
            vulnerabilities.append(errata_info._asdict())

        res = {"packages": vulnerabilities}

        return res, 200
