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


from enum import Enum
from typing import Any, NamedTuple, Optional

from .base import JSONObject, JSONValue, ErrataServer, ErrataServerError
from .serde import serialize_enum, deserialize_enum, serialize, deserialize
from .result import Result


SA_LIST_ROUTE = "sa"
SA_CREATE_ROUTE = "sa/create"
SA_DISCARD_ROUTE = "sa/discard"
SA_UPDATE_ROUTE = "sa/update"


class SaType(Enum):
    ADVISORY = "advisory"
    EXCLUSION = "exclusion"
    PATCH = "patch"

    def serialize(self) -> str:
        return serialize_enum(self)

    @staticmethod
    def deserialize(value: JSONValue) -> Result["SaType", str]:
        return deserialize_enum(SaType, value)  # type: ignore


class SaAction(Enum):
    CVE = "cve"
    CPE = "cpe"
    PACKAGE = "package"
    VULNERABILITY = "vulnerability"

    def serialize(self) -> str:
        return serialize_enum(self)

    @staticmethod
    def deserialize(value: JSONValue) -> Result["SaAction", str]:
        return deserialize_enum(SaAction, value)  # type: ignore


class SaReferenceType(Enum):
    ERRATA = "errata"
    VULN = "vuln"
    BUG = "bug"
    WEB = "web"

    def serialize(self) -> str:
        return serialize_enum(self)

    @staticmethod
    def deserialize(value: JSONValue) -> Result["SaReferenceType", str]:
        return deserialize_enum(SaReferenceType, value)  # type: ignore

    def __lt__(self, other):
        if isinstance(other, SaReferenceType):
            return _SA_REF_TYPE_CMP[self] < _SA_REF_TYPE_CMP[other]
        return NotImplemented


_SA_REF_TYPE_CMP = {
    SaReferenceType.ERRATA: 0,
    SaReferenceType.VULN: 1,
    SaReferenceType.BUG: 2,
    SaReferenceType.WEB: 3,
}


class UserInfo(NamedTuple):
    name: str
    ip: str


class ChangeReason(NamedTuple):
    actor: str
    user: UserInfo
    message: str
    details: dict[str, str]


class ErrataChange(NamedTuple):
    id: str
    created: str
    updated: str
    user: str
    user_ip: str
    reason: ChangeReason
    type: str
    source: str
    origin: str
    errata_id: str
    transaction_id: str


class Reference(NamedTuple):
    type: str
    link: str


class SaReference(NamedTuple):
    type: SaReferenceType
    link: str


class PkgVersionRange(NamedTuple):
    begin: str = ""
    begin_exclude: bool = False
    end: str = ""
    end_exclude: bool = False


class ErrataJson(NamedTuple):
    type: SaType
    action: SaAction
    is_public: bool
    reason: str
    description: str
    vuln_id: str
    vuln_cpe: Optional[str] = None
    branches: list[str] = list()
    pkg_name: str = ""
    pkg_evr: str = ""
    pkg_versions: list[PkgVersionRange] = list()
    references: list[SaReference] = list()
    extra: Optional[dict[str, str]] = None

    def sorted(self) -> "ErrataJson":
        """Sorts ErratJosn fields to maintain stable hashing."""
        sorted_extra = (
            {k: v for k, v in ((k, self.extra[k]) for k in sorted(self.extra.keys()))}
            if self.extra is not None
            else None
        )
        return ErrataJson(
            type=self.type,
            action=self.action,
            is_public=self.is_public,
            reason=self.reason,
            description=self.description,
            vuln_id=self.vuln_id,
            vuln_cpe=self.vuln_cpe,
            branches=sorted(self.branches),
            pkg_name=self.pkg_name,
            pkg_evr=self.pkg_evr,
            pkg_versions=sorted(self.pkg_versions),
            references=sorted(self.references),
            extra=sorted_extra,
        )


ErrataJson.SKIP_SERILIZING_IF_NONE = True  # type: ignore


def sanitize_ej(e: ErrataJson) -> ErrataJson:
    """Fix ErrataJson.extra filed contents if it is an empty dict."""
    if e.extra or e.extra is None:
        return e
    # replace an empty dictionary in `extra` field to None
    return e._replace(extra=None)


class ErrataHistory(NamedTuple):
    id: str
    hash: str
    type: str
    source: str
    created: str
    updated: str
    references: list[Reference]
    json: Optional[ErrataJson]
    pkg_hash: str
    pkg_name: str
    pkg_version: str
    pkg_release: str
    pkgset_name: str
    task_id: int
    subtask_id: int
    task_state: str

    @property
    def branch(self) -> str:
        return self.pkgset_name


class Errata(NamedTuple):
    eh: ErrataHistory
    is_discarded: bool

    def asdict(self) -> dict[str, Any]:
        s = serialize(self)  # type: ignore
        res: dict[str, Any] = s["eh"]  # type: ignore
        res["is_discarded"] = s["is_discarded"]
        return res


class AffectedPCM(NamedTuple):
    package: str
    cve: str


class SaManageResponse(NamedTuple):
    result: str
    errata: list[ErrataHistory]
    errata_change: list[ErrataChange]
    affected_pcm: list[AffectedPCM]


class ErrataSAService:
    """Errata SA manage service interface class."""

    def __init__(
        self, url: str, access_token: str, user: str, ip: str, dry_run: bool
    ) -> None:
        self.server = ErrataServer(url)
        self.user = user
        self.user_ip = ip
        self.dry_run = dry_run
        self.access_token = access_token

    def list(self) -> list[Errata]:
        res = []
        response: list[JSONObject] = self.server.get(SA_LIST_ROUTE)  # type: ignore
        for el in [deserialize(Errata, e) for e in response]:
            if el.is_err():
                raise ErrataServerError(el.error)  # type: ignore
            else:
                res.append(el.unwrap())
        return res

    def create(self, errata_json: ErrataJson) -> SaManageResponse:
        dry_run_str = "true" if self.dry_run else "false"
        response = self.server.post(
            SA_CREATE_ROUTE,
            params={
                "user": self.user,
                "user_ip": self.user_ip,
                "dry_run": dry_run_str,
                "access_token": self.access_token,
            },
            json={"errata_json": serialize(sanitize_ej(errata_json))},  # type: ignore
        )
        d = deserialize(SaManageResponse, response)  # type: ignore
        if d.is_err():
            raise ErrataServerError(d.error)  # type: ignore
        return d.unwrap()

    def discard(self, reason: str, errata_json: ErrataJson) -> SaManageResponse:
        dry_run_str = "true" if self.dry_run else "false"
        response = self.server.post(
            SA_DISCARD_ROUTE,
            params={
                "user": self.user,
                "user_ip": self.user_ip,
                "dry_run": dry_run_str,
                "access_token": self.access_token,
            },
            json={"reason": reason, "errata_json": serialize(sanitize_ej(errata_json))},  # type: ignore
        )
        d = deserialize(SaManageResponse, response)  # type: ignore
        if d.is_err():
            raise ErrataServerError(d.error)  # type: ignore
        return d.unwrap()

    def update(
        self, reason: str, prev_errata_json: ErrataJson, errata_json: ErrataJson
    ) -> SaManageResponse:
        dry_run_str = "true" if self.dry_run else "false"
        response = self.server.post(
            SA_UPDATE_ROUTE,
            params={
                "user": self.user,
                "user_ip": self.user_ip,
                "dry_run": dry_run_str,
                "access_token": self.access_token,
            },
            json={
                "reason": reason,
                "prev_errata_json": serialize(sanitize_ej(prev_errata_json)),  # type: ignore
                "errata_json": serialize(sanitize_ej(errata_json)),  # type: ignore
            },
        )
        d = deserialize(SaManageResponse, response)  # type: ignore
        if d.is_err():
            raise ErrataServerError(d.error)  # type: ignore
        return d.unwrap()
