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

import re

from enum import Enum
from typing import NamedTuple, Optional

from altrepo_api.api.base import APIWorker
from altrepo_api.api.misc import lut
from altrepo_api.settings import namespace as settings
from altrepo_api.utils import get_logger
from altrepo_api.libs.pagination import Paginator
from altrepo_api.libs.sorting import rich_sort
from altrepo_api.libs.errata_server.errata_sa_service import (
    Errata,
    ErrataServerError,
    ErrataSAService,
    UserInfo,
)


_advisory_input_match = re.compile(
    r"(^CVE-\d{4}-\d{4,}$)|(^BDU:\d{4}-\d{5}$)|(^ALT-SA-\d{4}-\d{4,}-\d{1,}$)"
)

logger = get_logger(__name__)


def get_errata_service() -> ErrataSAService:
    try:
        return ErrataSAService(
            url=settings.ERRATA_MANAGE_URL,
            access_token="",
            user=UserInfo(name="", ip=""),
            dry_run=True,
        )
    except ErrataServerError as e:
        logger.error(f"Failed to connect to ErrataSA service: {e}")
        raise RuntimeError("error: %s" % e)


class ErrataRecordState(Enum):
    ALL = "all"
    ACTIVE = "active"
    INACTIVE = "inactive"


class ErrataJsonType(Enum):
    ALL = "all"
    CVE = "cve"
    CPE = "cpe"
    PACKAGE = "package"
    ADVISORY = "advisory"


class AdvisoryErrataArgs(NamedTuple):
    branch: Optional[str] = None
    input: Optional[str] = None
    sort: Optional[list[str]] = None
    page: Optional[int] = None
    limit: Optional[int] = None
    public_only: bool = True


class AdvisoryErrata(APIWorker):
    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.kwargs = kwargs
        self.args: AdvisoryErrataArgs
        super().__init__()

    def check_params(self) -> bool:
        self.logger.debug(f"args : {self.kwargs}")
        self.args = AdvisoryErrataArgs(**self.kwargs)

        if self.args.input:
            if not _advisory_input_match.match(self.args.input):
                self.validation_results.append(
                    f"Invalid input value: {self.args.input}. "
                    "Should be a valid CVE ID, BDU ID or Advisory Errata ID."
                )
        return self.validation_results == []

    def _build_filter(self):
        def filter_by_state(errata: Errata):
            return errata.is_discarded is False

        def filter_by_publicity(errata: Errata):
            return errata.eh.json.is_public is True  # type: ignore

        def filter_by_errata_id(errata: Errata, id: str):
            return errata.eh.id == id

        def filter_by_vuln_id(errata: Errata, id: str):
            return id in {
                r.link
                for r in errata.eh.references
                if r.type == lut.errata_ref_type_vuln
            }

        def filter_by_branch(errata: Errata, branch: str):
            branches = {
                r.link
                for r in errata.eh.references
                if r.type == lut.errata_ref_type_branch
            }
            return branch in branches or branches == {"*"}

        filters = [filter_by_state, filter_by_publicity]

        if self.args.branch:
            filters.append(lambda errata: filter_by_branch(errata, self.args.branch))  # type: ignore

        if self.args.input is not None:
            v = self.args.input
            if v.startswith(lut.errata_advisory_prefix):
                filters.append(lambda errata: filter_by_errata_id(errata, v))
            else:
                filters.append(lambda errata: filter_by_vuln_id(errata, v))

        return lambda errata: all(f(errata) for f in filters)

    def get(self):
        service = get_errata_service()
        try:
            erratas = service.list()
        except ErrataServerError as e:
            return self.store_error(
                {"message": f"Failed to get records from Errata Server: {e}"},
                severity=self.LL.ERROR,
                http_code=e.status_code or 500,
            )

        res = []

        filter_fn = self._build_filter()

        for errata in erratas:
            if filter_fn(errata):
                # replace empty nullable ErrataJson `extra` filed
                e = errata.asdict()
                if e.get("json", {}).get("extra") is None:
                    e["json"]["extra"] = {}
                res.append(e)

        if not res:
            return self.store_error(
                {"message": f"No data found in DB for {self.kwargs}"}, http_code=404
            )

        if self.args.sort:
            res = rich_sort(res, self.args.sort)

        paginator = Paginator(res, self.args.limit)
        res = paginator.get_page(self.args.page)

        return (
            {"request_args": self.args._asdict(), "length": len(res), "erratas": res},
            200,
            {
                "Access-Control-Expose-Headers": "X-Total-Count",
                "X-Total-Count": int(paginator.count),
            },
        )
