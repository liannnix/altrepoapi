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

from dataclasses import dataclass
from enum import Enum
from uuid import UUID, uuid4

from altrepo_api.utils import get_logger

from .base import (
    PncChangeRecord,
    PncRecord,
    PncManageError,
    ChangeReason,
    ChangeOrigin,
    ChangeSource,
    ChangeType,
    RollbackCB,
)
from .constants import PNC_STATE_ACTIVE, PNC_STATE_INACTIVE, PNC_STATE_CANDIDATE


logger = get_logger(__name__)


class PncType(Enum):
    CPE = "cpe"
    NAME = "name"


class PncAction(Enum):
    NONE = "none"
    CREATE = "create"
    UPDATE = "update"
    DISCARD = "discard"


@dataclass
class PncUpdate:
    pnc: PncRecord
    type: PncType
    action: PncAction


def _build_pnc_change(
    *,
    id: UUID,
    pnc: PncRecord,
    reason: ChangeReason,
    type: ChangeType,
    source: ChangeSource,
    origin: ChangeOrigin,
) -> PncChangeRecord:
    logger.info(
        f"Build `PackageNameConversion` change history record: {pnc} "
        f"[{type.name}, {source.name}, {origin.name}]"
    )
    return PncChangeRecord(
        id=id,
        reason=reason,
        type=type,
        source=source,
        origin=origin,
        pnc=pnc,
    )


class Transaction:
    def __init__(self, source: ChangeSource) -> None:
        self._id = uuid4()
        self._reason: ChangeReason
        self._pnc_updates: list[PncUpdate] = list()
        self._pnc_change_records: list[PncChangeRecord] = list()
        self._source = source

    @property
    def id(self):
        return self._id

    @property
    def pnc_records(self) -> list[PncRecord]:
        return [x.pnc for x in self._pnc_updates]

    @property
    def pnc_change_records(self) -> list[PncChangeRecord]:
        return self._pnc_change_records

    def register_pnc_create(self, pnc: PncRecord, pnc_type: PncType) -> None:
        if pnc.pnc_state not in (PNC_STATE_ACTIVE, PNC_STATE_CANDIDATE):
            raise PncManageError(f"Invalid record' `state`: {pnc.pnc_state}")
        self._pnc_updates.append(
            PncUpdate(pnc=pnc, type=pnc_type, action=PncAction.CREATE)
        )

    def register_pnc_update(self, pnc: PncRecord, pnc_type: PncType) -> None:
        if pnc.pnc_state != PNC_STATE_ACTIVE:
            raise PncManageError(f"Invalid record' `state`: {pnc.pnc_state}")
        self._pnc_updates.append(
            PncUpdate(pnc=pnc, type=pnc_type, action=PncAction.UPDATE)
        )

    def register_pnc_discard(self, pnc: PncRecord, pnc_type: PncType) -> None:
        if pnc.pnc_state != PNC_STATE_INACTIVE:
            raise PncManageError(f"Invalid record' `state`: {pnc.pnc_state}")
        self._pnc_updates.append(
            PncUpdate(pnc=pnc, type=pnc_type, action=PncAction.DISCARD)
        )

    def commit(self, reason: ChangeReason) -> None:
        self._reason = reason
        logger.info("Commtinig PNC manage transaction")
        # build errata history records
        self._handle_pnc_records()

    def rollback(self, rollback_cb: RollbackCB) -> bool:
        # XXX: delete all related DB records using transaction UUID here!
        logger.warning("PNC manage transaction rollback")
        return rollback_cb(self.id)

    def _handle_pnc_create(self, pnc_update: PncUpdate) -> None:
        self._pnc_change_records.append(
            _build_pnc_change(
                id=self.id,
                pnc=pnc_update.pnc,
                reason=self._reason,
                type=ChangeType.CREATE,
                source=self._source,
                origin=ChangeOrigin.PARENT,
            )
        )

    def _handle_pnc_update(self, pnc_update: PncUpdate) -> None:
        self._pnc_change_records.append(
            _build_pnc_change(
                id=self.id,
                pnc=pnc_update.pnc,
                reason=self._reason,
                type=ChangeType.UPDATE,
                source=self._source,
                origin=ChangeOrigin.PARENT,
            )
        )

    def _handle_pnc_discard(self, pnc_update: PncUpdate) -> None:
        self._pnc_change_records.append(
            _build_pnc_change(
                id=self.id,
                pnc=pnc_update.pnc,
                reason=self._reason,
                type=ChangeType.DISCARD,
                source=self._source,
                origin=ChangeOrigin.PARENT,
            )
        )

    def _handle_pnc_records(self) -> None:
        handlers = {
            PncAction.CREATE: self._handle_pnc_create,
            PncAction.UPDATE: self._handle_pnc_update,
            PncAction.DISCARD: self._handle_pnc_discard,
        }
        for pu in self._pnc_updates:
            handlers[pu.action](pu)
