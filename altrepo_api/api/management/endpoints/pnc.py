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

from altrepo_api.api.base import APIWorker, WorkerResult
from altrepo_api.api.metadata import KnownFilterTypes, MetadataChoiceItem, MetadataItem
from altrepo_api.api.misc import lut
from altrepo_api.settings import namespace as settings
from altrepo_api.utils import (
    get_logger,
    get_real_ip,
    make_tmp_table_name,
    sort_branches,
)

from .common.base import PncListElement, PncPackage, PncRecord
from .common.constants import (
    CHANGE_ACTION_CREATE,
    CHANGE_ACTION_DISCARD,
    CHANGE_ACTION_UPDATE,
    DRY_RUN_KEY,
    PNC_STATES,
    PNC_STATE_ACTIVE,
    PNC_STATE_INACTIVE,
    PNC_SOURCES,
)
from .common.utils import validate_action
from ..parsers import pnc_list_args
from ..sql import sql

from altrepo_api.libs.errata_server import ErrataServerError, UserInfo
from altrepo_api.libs.errata_server.pnc_manage_service import (
    PncManageService,
    serialize,
)


logger = get_logger(__name__)


def get_pnc_manage_service(
    *, dry_run: bool, access_token: str, user: UserInfo
) -> PncManageService:
    try:
        return PncManageService(
            url=settings.ERRATA_MANAGE_URL,
            access_token=access_token,
            user=user,
            dry_run=dry_run,
        )
    except ErrataServerError as e:
        logger.error(f"Failed to connect to Errata Server: {e}")
        raise RuntimeError("error: %s" % e)


class ManagePnc(APIWorker):
    def __init__(self, connection, payload, **kwargs):
        self.payload: dict[str, Any] = payload
        self.dry_run = kwargs.get(DRY_RUN_KEY, True)
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        # values set in self.check_params_xxx() call
        self.user: UserInfo
        self.package_name: str
        self.project_name: str
        self.reason: str
        self.action: str
        super().__init__()

    def _valiadte_and_parse(self):
        """Validate and parse `self.payload' JSON contents."""

        pnc: dict[str, str] = self.payload.get("pnc", {})
        if not pnc:
            self.validation_results.append("No PNC record object found")
            return

        try:
            package_name = pnc["package_name"]
            project_name = pnc["project_name"]
            pnc_state = pnc["state"]
            pnc_source = pnc["source"]

            if not (package_name and project_name):
                raise ValueError("Required fields values are empty")

            if pnc_state not in PNC_STATES:
                raise ValueError(f"Invalid PNC record state: {pnc_state}")

            if pnc_source not in PNC_SOURCES:
                raise ValueError(f"Invalid PNC record source: {pnc_source}")
        except Exception as e:
            self.validation_results.append(
                f"Failed to parse PNC record object {pnc}: {e}"
            )
            return

        self.package_name = package_name
        self.project_name = project_name

        self.user = UserInfo(
            name=self.payload.get("user", ""),
            ip=get_real_ip(),
        )

        self.action = self.payload.get("action", "")
        self.reason = self.payload.get("reason", "")

        if not self.user.name:
            self.validation_results.append("User name should be specified")

        if not self.reason:
            self.validation_results.append("PNC change reason should be specified")

        if not validate_action(self.action):
            self.validation_results.append(
                f"PNC change action '{self.action}' not supported"
            )

    def check_params_post(self) -> bool:
        self._valiadte_and_parse()

        if self.validation_results != []:
            return False

        if not self.action == CHANGE_ACTION_CREATE:
            self.validation_results.append("Change action validation error")

        if self.validation_results != []:
            return False
        return True

    def check_params_put(self) -> bool:
        self._valiadte_and_parse()

        if self.validation_results != []:
            return False

        if not self.action == CHANGE_ACTION_UPDATE:
            self.validation_results.append("Change action validation error")

        if self.validation_results != []:
            return False
        return True

    def check_params_delete(self) -> bool:
        self._valiadte_and_parse()

        if self.validation_results != []:
            return False

        if not self.action == CHANGE_ACTION_DISCARD:
            self.validation_results.append("Change action validation error")

        if self.validation_results != []:
            return False
        return True

    def get(self):
        """Get package to project mapping records, by package name, project name or
        record state if specified."""

        package_name = self.args.get("package_name")
        project_name = self.args.get("project_name")

        state = self.args.get("state")
        if state == "all":
            state = None

        service = get_pnc_manage_service(
            dry_run=True, access_token="", user=UserInfo("", "")
        )

        try:
            response = service.get(package_name, project_name, state)
        except ErrataServerError as e:
            return self.store_error(
                {"message": f"Failed to get data from Errata Server: {e}"},
                severity=self.LL.ERROR,
                http_code=e.status_code or 500,
            )

        return {
            "request_args": self.args,
            "length": len(response.pncs),
            "pncs": [serialize(r) for r in response.pncs],
        }, 200

    def post(self):
        """Handles package to project mapping PNC records create.
        Returns:
            - 200 (OK) if PNC record created successfully
            - 400 (Bad request) on paload validation errors
            - 409 (Conflict) if such PNC record exists already in DB
        """

        service = get_pnc_manage_service(
            dry_run=self.dry_run,
            access_token=settings.ERRATA_SERVER_TOKEN,
            user=self.user,
        )

        try:
            response = service.create(self.reason, self.package_name, self.project_name)
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

        affected = [
            {"package": pkg, "cves": sorted(cves)} for pkg, cves in affected.items()
        ]

        return {
            "user": self.user.name,
            "action": self.action,
            "reason": self.reason,
            "message": response.result,
            "pnc_records": [serialize(r) for r in response.pnc],
            "pnc_change_records": pnc_change_records,
            "affected": affected,
            "related_cve_ids": related_cve_ids,
        }, 200

    def put(self):
        return "OK", 200

    def delete(self):
        """Handles package to project mapping PNC records discard.
        Returns:
            - 200 (OK) if PNC record discarded successfully
            - 400 (Bad request) on paload validation errors
            - 409 (Conflict) if such PNC record exists already in DB
        """

        service = get_pnc_manage_service(
            dry_run=self.dry_run,
            access_token=settings.ERRATA_SERVER_TOKEN,
            user=self.user,
        )

        try:
            response = service.discard(
                self.reason, self.package_name, self.project_name
            )
        except ErrataServerError as e:
            return self.store_error(
                {"message": f"Failed to discard PNC records: {e}"},
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

        affected = [
            {"package": pkg, "cves": sorted(cves)} for pkg, cves in affected.items()
        ]

        return {
            "user": self.user.name,
            "action": self.action,
            "reason": self.reason,
            "message": response.result,
            "pnc_records": [serialize(r) for r in response.pnc],
            "pnc_change_records": pnc_change_records,
            "affected": affected,
            "related_cve_ids": related_cve_ids,
        }, 200


class PncListArgs(NamedTuple):
    state: str
    input: Optional[str] = None
    branch: Optional[str] = None
    page: Optional[int] = None
    limit: Optional[int] = None


class PncList(APIWorker):
    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.kwargs = kwargs
        self.args: PncListArgs
        self.sql = sql
        super().__init__()

    def check_params(self):
        self.args = PncListArgs(**self.kwargs)
        self.logger.debug(f"args : {self.kwargs}")

        if (
            self.args.branch is not None
            and self.args.branch not in lut.repology_branch_map
        ):
            self.validation_results.append(f"Invalid branch: {self.args.branch}")
            return False

        return True

    @property
    def _input(self) -> str:
        if self.args.input:
            return f"arrayExists(x -> (x.1 ILIKE '%{self.args.input}%'), pkgs) OR result ILIKE '%{self.args.input}%'"
        return ""

    @property
    def _state(self) -> str:
        if self.args.state != "all":
            return f"state = '{self.args.state}'"
        return ""

    @property
    def _branches(self) -> tuple[str, ...]:
        if self.args.branch:
            return (lut.repology_branch_map[self.args.branch],)
        return lut.repology_branches

    @property
    def _limit(self) -> str:
        return f"LIMIT {self.args.limit}" if self.args.limit else ""

    @property
    def _page(self) -> str:
        if self.args.limit and self.args.page:
            page = self.args.page
            per_page = self.args.limit
            offset = (page - 1) * per_page
            return f"OFFSET {offset}"
        return ""

    @property
    def _where_clause(self) -> str:
        conditions = []

        if self._input:
            conditions.append(self._input)

        if self._state:
            conditions.append(self._state)

        if conditions:
            return "WHERE " + " AND ".join(conditions)
        return ""

    def _get_cpes(self, pncs: list[dict[str, Any]]):
        self.status = False
        projects: dict[tuple[str, str], dict[str, Any]] = {
            (el["pnc_result"], el["pnc_state"]): el for el in pncs
        }
        tmp_table = make_tmp_table_name("project_names")
        response = self.send_sql_request(
            self.sql.get_cpes_by_project_names.format(
                tmp_table=tmp_table, cpe_states=PNC_STATES
            ),
            external_tables=[
                {
                    "name": tmp_table,
                    "structure": [
                        ("project_name", "String"),
                    ],
                    "data": [{"project_name": el[0]} for el in projects.keys()],
                },
            ],
        )
        if not self.sql_status:
            return []
        if response:
            for p in (PncRecord(*el) for el in response):
                if (p.pkg_name, PNC_STATE_INACTIVE) in projects:
                    projects[(p.pkg_name, PNC_STATE_INACTIVE)].setdefault(
                        "cpes", []
                    ).append(p.asdict())
                if (p.pkg_name, PNC_STATE_ACTIVE) in projects:
                    projects[(p.pkg_name, PNC_STATE_ACTIVE)].setdefault(
                        "cpes", []
                    ).append(p.asdict())
        self.status = True
        return list(projects.values())

    def get(self):
        # get PNC records from DB
        response = self.send_sql_request(
            self.sql.get_pnc_list.format(
                where_clause=self._where_clause,
                branch=self._branches,
                pnc_branches=tuple(lut.repology_branches),
                limit=self._limit,
                page=self._page,
            )
        )
        if not self.sql_status:
            return self.error

        pnc_records = [
            PncListElement(state, result, [PncPackage(*pkg) for pkg in pkgs]).asdict()
            for state, result, pkgs, _ in response
        ]

        if not pnc_records:
            return self.store_error(
                {"message": f"No data found in DB for {self.args}"}, http_code=404
            )

        pnc_records = self._get_cpes(pnc_records)
        if not self.status:
            return self.error

        return (
            {"request_args": self.args._asdict(), "pncs": pnc_records},
            200,
            {
                "Access-Control-Expose-Headers": "X-Total-Count",
                "X-Total-Count": int(response[0][-1]),
            },
        )

    def metadata(self) -> WorkerResult:
        metadata = []
        for args in pnc_list_args.args:
            item_info = {
                "name": args.name,
                "label": args.name.replace("_", " ").capitalize(),
                "help_text": args.help,
            }
            if args.name == "state":
                metadata.append(
                    MetadataItem(
                        **item_info,
                        type=KnownFilterTypes.CHOICE,
                        choices=[
                            MetadataChoiceItem(
                                value=choice, display_name=choice.capitalize()
                            )
                            for choice in args.choices
                            if choice != "all"
                        ],
                    )
                )

            if args.name == "branch":
                metadata.append(
                    MetadataItem(
                        **item_info,
                        type=KnownFilterTypes.CHOICE,
                        choices=[
                            MetadataChoiceItem(value=choice, display_name=choice)
                            for choice in sort_branches(lut.repology_branch_map)
                        ],
                    )
                )

        return {
            "length": len(metadata),
            "metadata": [el.asdict() for el in metadata],
        }, 200
