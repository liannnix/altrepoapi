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
from __future__ import annotations

from typing import NamedTuple

from .base import (
    ErrataServerConnection,
    ErrataServerError,  # noqa: F401
)
from .errata_sa_service import ErrataHistory, Reference
from .serde import deserialize

ERRATA_REFRESH_ROUTE = "errata/refresh"


class ReferencesPatch(NamedTuple):
    add_bugs: list[Reference]
    del_bugs: list[Reference]
    add_vulns: list[Reference]
    del_vulns: list[Reference]

    @staticmethod
    def from_history(old: list[Reference], new: list[Reference]) -> ReferencesPatch:
        old_bugs = {r for r in old if r.type == "bug"}
        old_vulns = {r for r in old if r.type == "vuln"}
        new_bugs = {r for r in new if r.type == "bug"}
        new_vulns = {r for r in new if r.type == "vuln"}

        return ReferencesPatch(
            add_bugs=sorted(new_bugs - old_bugs),
            del_bugs=sorted(old_bugs - new_bugs),
            add_vulns=sorted(new_vulns - old_vulns),
            del_vulns=sorted(old_vulns - new_vulns),
        )


class ErrataRefreshResult(NamedTuple):
    change_type: str
    errata: ErrataHistory
    patch: ReferencesPatch


class ErrataRefreshServiceCollectResult(NamedTuple):
    results: list[ErrataRefreshResult]


class ErrataRefreshService:
    """Errata Refresh service interface class."""

    def __init__(self, url: str, access_token: str, user: str, ip: str) -> None:
        self.server = ErrataServerConnection(url)
        self.user = user
        self.user_ip = ip
        self.access_token = access_token

    def collect(self) -> ErrataRefreshServiceCollectResult:
        return (
            self.server.post(
                ERRATA_REFRESH_ROUTE,
                params={
                    "user": self.user,
                    "user_ip": self.user_ip,
                    "commit": False,
                    "access_token": self.access_token,
                },
            )
            .and_then(lambda r: deserialize(ErrataRefreshServiceCollectResult, r))  # type: ignore
            .unwrap()
        )
