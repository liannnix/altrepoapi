# ALTRepo API
# Copyright (C) 2021-2026  BaseALT Ltd

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

from typing import Any, NamedTuple, Optional

from altrepo_api.api.vulnerabilities.endpoints.common import CPE

from altrepo_api.api.base import APIWorker, WorkerResult
from altrepo_api.api.metadata import KnownFilterTypes, MetadataChoiceItem, MetadataItem
from altrepo_api.api.misc import lut
from altrepo_api.libs.errata_server import ErrataServerError, UserInfo
from altrepo_api.libs.errata_server.cpe_manage_service import (
    CpeManageService,
    serialize,
)
from altrepo_api.libs.pagination import Paginator
from altrepo_api.libs.sorting import rich_sort
from altrepo_api.settings import namespace as settings
from altrepo_api.utils import get_logger, get_real_ip

from .common.constants import (
    CHANGE_ACTION_CREATE,
    CHANGE_ACTION_DISCARD,
    CHANGE_ACTION_UPDATE,
    DRY_RUN_KEY,
    PNC_STATES,
    PNC_STATE_CANDIDATE,
)
from .common.utils import validate_action, validate_branch_with_tasks
from ..parsers import cpe_list_args
from ..sql import sql


JOIN_TYPE_INNER = "INNER"
JOIN_TYPE_LEFT = "LEFT"
BRANCH_NONE = "none"


logger = get_logger(__name__)


def get_cpe_manage_service(
    *, dry_run: bool, access_token: str, user: UserInfo
) -> CpeManageService:
    try:
        return CpeManageService(
            url=settings.ERRATA_MANAGE_URL,
            access_token=access_token,
            user=user,
            dry_run=dry_run,
        )
    except ErrataServerError as e:
        logger.error(f"Failed to connect to Errata Server: {e}")
        raise RuntimeError("error: %s" % e)


class CpeRaw(NamedTuple):
    state: str
    name: str
    repology_name: str
    repology_branch: str
    cpe: str


class CPECandidates(APIWorker):
    """Retrieves CPE candidates records."""

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        return True

    def get(self):
        cpes: dict[tuple[str, str], Any] = {}

        all_candidates = self.args.get("all", False)
        limit = self.args.get("limit")
        page = self.args.get("page")

        sql = self.sql.get_cpes.format(
            cpe_branches=lut.repology_branches,
            pkg_name_conversion_clause="",
            cpe_states=(PNC_STATE_CANDIDATE,),
            join_type=JOIN_TYPE_LEFT if all_candidates else JOIN_TYPE_INNER,
        )

        response = self.send_sql_request(sql)
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error({"Error": "No CPE candidates found in DB"})

        for el in response:
            try:
                cpe_raw = CpeRaw(*el)

                branch = lut.repology_reverse_branch_map.get(
                    cpe_raw.repology_branch, [BRANCH_NONE]
                )[0]
                cpe = CPE(cpe_raw.cpe)
                cpe_s = str(cpe)

                if cpe.vendor == "*" or cpe.product == "*":
                    self.logger.info(f"Skip malformed CPE candidate: {el}")
                    continue

                if (cpe_s, cpe_raw.repology_name) not in cpes:
                    cpes[(cpe_s, cpe_raw.repology_name)] = {
                        "state": cpe_raw.state,
                        "packages": (
                            [{"name": cpe_raw.name, "branch": branch}]
                            if branch != BRANCH_NONE
                            else []
                        ),
                    }
                else:
                    cpes[(cpe_s, cpe_raw.repology_name)]["packages"].append(
                        {"name": cpe_raw.name, "branch": branch}
                    )
            except (TypeError, ValueError):
                self.logger.info(f"Failed to parse CPE from {el}")
                continue

        cpes_list = [{"cpe": k[0], "project_name": k[1], **v} for k, v in cpes.items()]

        paginator = Paginator(cpes_list, limit)
        res = paginator.get_page(page)

        res = {
            "length": len(res),
            "cpes": res,
        }

        return (
            res,
            200,
            {
                "Access-Control-Expose-Headers": "X-Total-Count",
                "X-Total-Count": int(paginator.count),
            },
        )


class ManageCpe(APIWorker):
    """CPE records management handler."""

    def __init__(self, connection, payload, **kwargs):
        self.payload: dict[str, Any] = payload
        self.dry_run = kwargs.get(DRY_RUN_KEY, True)
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        # values set in self.check_params_xxx() call
        self.cpe: CPE
        self.project_name: str
        self.state: str
        self.package_name: Optional[str]
        self.user: UserInfo
        self.action: str
        self.reason: str
        super().__init__()

    def _valiadte_and_parse(self):
        """Validate and parse `self.payload' JSON contents."""

        cpe: dict[str, str] = self.payload.get("cpe", {})
        if not cpe:
            self.validation_results.append("No CPE records object found")
            return

        try:
            cpe_ = CPE(cpe["cpe"])
            project_name = cpe["project_name"]
            cpe_state = cpe["state"]

            if not project_name or not cpe_state:
                raise ValueError("Required fields values are empty")

            if cpe_state not in PNC_STATES:
                raise ValueError(f"Invalid CPE record state: {cpe_state}")
        except Exception as e:
            self.validation_results.append(
                f"Failed to parse CPE record object {cpe}: {e}"
            )
            return

        self.cpe = cpe_
        self.state = cpe_state
        self.project_name = project_name
        self.package_name = self.args.get("package_name", None)

        self.user = UserInfo(
            name=self.payload.get("user", ""),
            ip=get_real_ip(),
        )

        self.action = self.payload.get("action", "")
        self.reason = self.payload.get("reason", "")

        if not self.user.name:
            self.validation_results.append("User name should be specified")

        if not self.reason:
            self.validation_results.append("CPE change reason should be specified")

        if not validate_action(self.action):
            self.validation_results.append(
                f"CPE change action '{self.action}' not supported"
            )

    def check_params(self):
        self.logger.debug(f"args : {self.args}")

        self.branch = self.args.get("branch", None)
        if self.branch is not None and not validate_branch_with_tasks(self.branch):
            self.validation_results.append(f"Invalid branch: {self.branch}")
            return False

        self.package_name = self.args["package_name"]

        return True

    def check_params_post(self) -> bool:
        self._valiadte_and_parse()

        if self.validation_results != []:
            return False

        if not self.action == CHANGE_ACTION_CREATE:
            self.validation_results.append("Change action validation error")

        return self.validation_results == []

    def check_params_put(self) -> bool:
        self._valiadte_and_parse()

        if self.validation_results != []:
            return False

        if not self.action == CHANGE_ACTION_UPDATE:
            self.validation_results.append("Change action validation error")

        return self.validation_results == []

    def check_params_delete(self) -> bool:
        self._valiadte_and_parse()

        if self.validation_results != []:
            return False

        if not self.action == CHANGE_ACTION_DISCARD:
            self.validation_results.append("Change action validation error")

        return self.validation_results == []

    def get(self):
        """Get CPE records, active and candidate, by package name
        and branch (optional)."""

        service = get_cpe_manage_service(
            dry_run=True, access_token="", user=UserInfo("", "")
        )

        try:
            assert self.package_name is not None
            response = service.get(self.package_name, self.branch, None)
        except ErrataServerError as e:
            return self.store_error(
                {"message": f"Failed to get data from Errata Server: {e}"},
                severity=self.LL.ERROR,
                http_code=e.status_code or 500,
            )

        return {
            "length": len(response.cpes),
            "name": self.package_name or "",
            "branch": self.branch or "",
            "cpes": [serialize(cpe) for cpe in response.cpes],
        }, 200

    def post(self):
        """Handles CPE records create.
        Returns:
            - 200 (OK) if CPE record created successfully
            - 400 (Bad request) on paload validation errors
            - 409 (Conflict) if such CPE record exists already in DB
        """

        service = get_cpe_manage_service(
            dry_run=self.dry_run,
            access_token=settings.ERRATA_SERVER_TOKEN,
            user=self.user,
        )

        try:
            response = service.create(
                self.reason, str(self.cpe), self.project_name, self.package_name
            )
        except ErrataServerError as e:
            return self.store_error(
                {"message": f"Failed to create PNC records: {e}"},
                severity=self.LL.ERROR,
                http_code=e.status_code or 500,
            )

        pnc_change_records = []
        for pncc in response.pnc_change:
            r = serialize(pncc)
            pnc_change_records.append({**r, "user": pncc.reason.user.name})

        affected = {}
        for pcm in response.affected_pcm:
            if pcm.package not in affected:
                affected[pcm.package] = [pcm.cve]

            if pcm.cve not in affected[pcm.package]:
                affected[pcm.package].append(pcm.cve)

        related_cve_ids = sorted({c for cves in affected.values() for c in cves})
        related_packages = sorted(affected.keys())

        return {
            "user": self.user.name,
            "action": self.action,
            "reason": self.reason,
            "message": response.result,
            "cpe": {
                "cpe": str(self.cpe),
                "project_name": self.project_name,
                "state": self.state,
            },
            "package_name": self.package_name or "",
            "cpe_records": [serialize(r) for r in response.pnc],
            "cpe_change_records": pnc_change_records,
            "related_packages": related_packages,
            "related_cve_ids": related_cve_ids,
        }, 200

    def put(self):
        """Handles CPE record update.
        Returns:
            - 200 (OK) if CPE record was updated or no changes found to be made
            - 400 (Bad request) on paload validation errors
            - 404 (Not found) if CPE record does not exists
        """

        if self.package_name:
            return self.store_error(
                {
                    "message": "'package_name' argument not supported here",
                    "package_name": self.package_name,
                },
                self.LL.WARNING,
                400,
            )

        service = get_cpe_manage_service(
            dry_run=self.dry_run,
            access_token=settings.ERRATA_SERVER_TOKEN,
            user=self.user,
        )

        try:
            response = service.update(self.reason, str(self.cpe), self.project_name)
        except ErrataServerError as e:
            return self.store_error(
                {"message": f"Failed to create PNC records: {e}"},
                severity=self.LL.ERROR,
                http_code=e.status_code or 500,
            )

        pnc_change_records = []
        for pncc in response.pnc_change:
            r = serialize(pncc)
            pnc_change_records.append({**r, "user": pncc.reason.user.name})

        affected = {}
        for pcm in response.affected_pcm:
            if pcm.package not in affected:
                affected[pcm.package] = [pcm.cve]

            if pcm.cve not in affected[pcm.package]:
                affected[pcm.package].append(pcm.cve)

        related_cve_ids = sorted({c for cves in affected.values() for c in cves})
        related_packages = sorted(affected.keys())

        return {
            "user": self.user.name,
            "action": self.action,
            "reason": self.reason,
            "message": response.result,
            "cpe": {
                "cpe": str(self.cpe),
                "project_name": self.project_name,
                "state": self.state,
            },
            "package_name": self.package_name or "",
            "cpe_records": [serialize(r) for r in response.pnc],
            "cpe_change_records": pnc_change_records,
            "related_packages": related_packages,
            "related_cve_ids": related_cve_ids,
        }, 200

    def delete(self):
        """Handles CPE record discard.
        Returns:
            - 200 (OK) if CPE record discarded successfully
            - 400 (Bad request) on paload validation errors
            - 404 (Not found) if CPE record is discarded already or does not exists
            - 409 (Conflict) if CPE state in 'active'
        """

        service = get_cpe_manage_service(
            dry_run=self.dry_run,
            access_token=settings.ERRATA_SERVER_TOKEN,
            user=self.user,
        )

        try:
            response = service.discard(
                self.reason, str(self.cpe), self.project_name, self.package_name
            )
        except ErrataServerError as e:
            return self.store_error(
                {"message": f"Failed to create PNC records: {e}"},
                severity=self.LL.ERROR,
                http_code=e.status_code or 500,
            )

        pnc_change_records = []
        for pncc in response.pnc_change:
            r = serialize(pncc)
            pnc_change_records.append({**r, "user": pncc.reason.user.name})

        affected = {}
        for pcm in response.affected_pcm:
            if pcm.package not in affected:
                affected[pcm.package] = [pcm.cve]

            if pcm.cve not in affected[pcm.package]:
                affected[pcm.package].append(pcm.cve)

        related_cve_ids = sorted({c for cves in affected.values() for c in cves})
        related_packages = sorted(affected.keys())

        return {
            "user": self.user.name,
            "action": self.action,
            "reason": self.reason,
            "message": response.result,
            "cpe": {
                "cpe": str(self.cpe),
                "project_name": self.project_name,
                "state": self.state,
            },
            "package_name": self.package_name or "",
            "cpe_records": [serialize(r) for r in response.pnc],
            "cpe_change_records": pnc_change_records,
            "related_packages": related_packages,
            "related_cve_ids": related_cve_ids,
        }, 200


class CPEListArgs(NamedTuple):
    is_discarded: bool
    input: Optional[str] = None
    limit: Optional[int] = None
    page: Optional[int] = None
    sort: Optional[list[str]] = None


class CPEList(APIWorker):
    """Retrieves CPE records."""

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.kwargs = kwargs
        self.args: CPEListArgs
        self.sql = sql
        super().__init__()

    def check_params(self):
        self.args = CPEListArgs(**self.kwargs)
        self.logger.debug(f"args : {self.kwargs}")
        return True

    @property
    def _where_condition(self) -> str:
        if self.args.input.startswith("CVE-"):  # type: ignore
            response = self.send_sql_request(
                self.sql.get_cpes_by_vulns.format(cves=[self.args.input])
            )
            return f"WHERE cpe IN {[el[0] for el in response]}"

        return (
            f"WHERE pkg_name ILIKE '%{self.args.input}%' "
            f"OR repology_name ILIKE '%{self.args.input}%' "
            f"OR cpe ILIKE '%{self.args.input}%'"
        )

    def metadata(self) -> WorkerResult:
        metadata = []
        for arg in cpe_list_args.args:
            item_info = {
                "name": arg.name,
                "label": arg.name.replace("_", " ").capitalize(),
                "help_text": arg.help,
            }

            if arg.type.__name__ == "boolean":
                metadata.append(
                    MetadataItem(
                        **item_info,
                        type=KnownFilterTypes.CHOICE,
                        choices=[
                            MetadataChoiceItem(value="true", display_name="True"),
                            MetadataChoiceItem(value="false", display_name="False"),
                        ],
                    )
                )

        return {
            "length": len(metadata),
            "metadata": [el.asdict() for el in metadata],
        }, 200

    def get(self):
        cpes: dict[tuple[str, str], Any] = {}
        state = "WHERE state = 'inactive'" if self.args.is_discarded else ""

        response = self.send_sql_request(
            self.sql.find_cpe.format(
                where=self._where_condition if self.args.input else "",
                state=state,
                pnc_branches=lut.repology_branches,
            )
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {
                    "message": "No data found in database for given parameters",
                    "args": self.args._asdict(),
                }
            )

        for el in response:
            try:
                cpe_raw = CpeRaw(*el)

                branch = lut.repology_reverse_branch_map[cpe_raw.repology_branch][0]
                cpe = CPE(cpe_raw.cpe)
                cpe_s = str(cpe)

                if cpe.vendor == "*" or cpe.product == "*":
                    self.logger.info(f"Skip malformed CPE candidate: {el}")
                    continue

                if (cpe_s, cpe_raw.repology_name) not in cpes:
                    cpes[(cpe_s, cpe_raw.repology_name)] = {
                        "state": cpe_raw.state,
                        "packages": [{"name": cpe_raw.name, "branch": branch}],
                    }
                else:
                    cpes[(cpe_s, cpe_raw.repology_name)]["packages"].append(
                        {"name": cpe_raw.name, "branch": branch}
                    )
            except (TypeError, ValueError):
                self.logger.info(f"Failed to parse CPE from {el}")
                continue

        result = [{"cpe": k[0], "project_name": k[1], **v} for k, v in cpes.items()]
        if self.args.sort:
            result = rich_sort(result, self.args.sort)

        paginator = Paginator(result, self.args.limit)
        page_obj = paginator.get_page(self.args.page)

        return (
            {
                "request_args": self.args._asdict(),
                "length": len(page_obj),
                "cpes": page_obj,
            },
            200,
            {
                "Access-Control-Expose-Headers": "X-Total-Count",
                "X-Total-Count": int(paginator.count),
            },
        )
