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
from functools import partial
from typing import Union
from uuid import UUID, uuid4

from altrepo_api.utils import get_logger

from .base import (
    Errata,
    ErrataID,
    ErrataChange,
    ChangeOrigin,
    ChangeSource,
    ChangeType,
    ErrataManageError,
    UserInfo,
    DBTransactionRollback,
)
from .constants import DT_NEVER

from .errata import (
    build_new_bulletin,
    update_bulletin_by_errata_add,
    update_bulletin_by_errata_update,
    update_bulletin_by_errata_discard,
)
from .errata_id import (
    ErrataIDServiceProtocol,
    ErrataIDServiceResult,
    # check_errata_id,
    update_errata_id,
    register_package_update_id,
    register_errata_change_id
)
from .helpers import Branch


logger = get_logger(__name__)


class ErrataType(Enum):
    PACKAGE = "package_update"
    BULLETIN = "branch_update"


class ErrataAction(Enum):
    NONE = "none"
    CREATE = "create"
    UPDATE = "update"
    DISCARD = "discard"


@dataclass
class ErrataUpdate:
    errata: Errata
    type: ErrataType
    action: ErrataAction
    old_eid: Union[ErrataID, None] = None
    new_eid: Union[ErrataID, None] = None
    year: int = 0
    branch: Branch = Branch("", DT_NEVER, 0)


def _build_errata_change(
    *,
    ec_id: ErrataIDServiceResult,
    errata: ErrataID,
    user_unfo: UserInfo,
    type: ChangeType,
    source: ChangeSource,
    origin: ChangeOrigin,
    transaction_id: UUID,
):
    logger.info(
        f"Build errata change history record: {ec_id.id} => {errata.id} "
        f"[{type.name}, {source.name}, {origin.name}]"
    )
    return ErrataChange(
        id=ErrataID.from_id(ec_id.id),
        created=ec_id.created,
        updated=ec_id.updated,
        user=user_unfo.name,
        user_ip=user_unfo.ip,
        reason=user_unfo.reason,
        type=type,
        source=source,
        origin=origin,
        errata_id=errata,
        transaction_id=transaction_id,
    )


def parse_uuid(u: Union[UUID, str, None]) -> UUID:
    if isinstance(u, UUID):
        return u
    if isinstance(u, str):
        return UUID(u)
    return uuid4()


class Transaction:
    def __init__(
        self,
        eid_service: ErrataIDServiceProtocol,
        transaction_id: UUID,
        dry_run: bool,
        change_source: ChangeSource
    ) -> None:
        self.eid_service = eid_service
        self.dry_run = dry_run
        self._user_info: UserInfo
        self._errata_update: ErrataUpdate
        self._bulletin_update: Union[ErrataUpdate, None] = None
        self._errata_history_records: dict[ErrataType, Errata] = dict()
        self._errata_change_records: list[ErrataChange] = list()
        self._ec_id: Union[str, None] = None
        self._id = transaction_id
        self._change_source = change_source

    @property
    def new_errata(self) -> Errata:
        try:
            return self._errata_history_records[ErrataType.PACKAGE]
        except KeyError:
            raise ErrataManageError("No value found for `new_errata`")

    @property
    def new_bulletin(self) -> Errata:
        try:
            return self._errata_history_records[ErrataType.PACKAGE]
        except KeyError:
            raise ErrataManageError("No value found for `new_bulletin`")

    @property
    def errata_action(self) -> ErrataAction:
        return self._errata_update.action

    @property
    def bulletin_action(self) -> ErrataAction:
        return (
            self._bulletin_update.action
            if self._bulletin_update is not None
            else ErrataAction.NONE
        )

    @property
    def errata_history_records(self) -> list[Errata]:
        return list(self._errata_history_records.values())

    @property
    def errata_change_records(self) -> list[ErrataChange]:
        return self._errata_change_records

    def register_errata_create(self, errata: Errata, year: int) -> None:
        self._errata_update = ErrataUpdate(
            errata=errata,
            type=ErrataType.PACKAGE,
            action=ErrataAction.CREATE,
            year=year,
        )

    def register_errata_update(self, errata: Errata) -> None:
        self._errata_update = ErrataUpdate(
            errata=errata,
            type=ErrataType.PACKAGE,
            action=ErrataAction.UPDATE,
            old_eid=errata.id,
        )

    def register_errata_discard(self, errata: Errata) -> None:
        self._errata_update = ErrataUpdate(
            errata=errata,
            type=ErrataType.PACKAGE,
            action=ErrataAction.DISCARD,
            old_eid=errata.id,
        )

    def register_bulletin_create(self, branch: Branch) -> None:
        self._bulletin_update = ErrataUpdate(
            errata=None,  # type: ignore
            type=ErrataType.BULLETIN,
            action=ErrataAction.CREATE,
            branch=branch,
        )

    def register_bulletin_update(self, bulletin: Errata) -> None:
        self._bulletin_update = ErrataUpdate(
            errata=bulletin,
            type=ErrataType.BULLETIN,
            action=ErrataAction.UPDATE,
            old_eid=bulletin.id,
        )

    def register_bulletin_discard(self, bulletin: Errata) -> None:
        self._bulletin_update = ErrataUpdate(
            errata=bulletin,
            type=ErrataType.BULLETIN,
            action=ErrataAction.DISCARD,
            old_eid=bulletin.id,
        )

    def commit(self, user_info: UserInfo, ec_id: Union[str, None]):
        self._ec_id = ec_id
        self._user_info = user_info
        logger.info("Commtinig errata manage transaction")
        # build errata history records
        {
            ErrataAction.CREATE: self._handle_errata_create,
            ErrataAction.UPDATE: self._handle_errata_update,
            ErrataAction.DISCARD: self._handle_errata_discard,
        }[self._errata_update.action]()
        # build errata change history records
        self._handle_errata_change_history()

    def rollback(self, sql_callback: DBTransactionRollback) -> bool:
        # XXX: delete DB records by transaction ID here!
        # FIXME: need to handle ErrataID service records rollback as well
        if self.dry_run:
            logger.warning("DRY_RUN: Errata manage transaction rollback")
            return True
        logger.warning("Errata manage transaction rollback")
        return sql_callback([self._id])

    def _handle_errata_change_history(self):
        # get new errata change ID if not provided
        if self._ec_id is None:
            _ec_id = register_errata_change_id(self.eid_service)
            logger.info(f"Registered new ErrataID: {_ec_id.id}")
        else:
            _ec_id = update_errata_id(self.eid_service, self._ec_id)
            logger.info(f"Updated ErrataID version: {_ec_id.id}")

        # build partally applied arguments functions
        pu_ec_fn = partial(
            _build_errata_change,
            ec_id=_ec_id,
            user_unfo=self._user_info,
            errata=self._errata_history_records[ErrataType.PACKAGE].id,  # type: ignore
            source=self._change_source,
            origin=ChangeOrigin.PARENT,
            transaction_id=self._id,
        )

        def stub_fn(*args, **kwargs) -> ErrataChange:
            return  # type: ignore

        if self.bulletin_action != ErrataAction.NONE:
            bu_ec_fn = partial(
                _build_errata_change,
                ec_id=_ec_id,
                user_unfo=self._user_info,
                errata=self._errata_history_records[ErrataType.BULLETIN].id,  # type: ignore
                source=ChangeSource.AUTO,
                origin=ChangeOrigin.CHILD,
                transaction_id=self._id,
            )
        else:
            bu_ec_fn = stub_fn

        # add errata change history record for package update
        if self.errata_action == ErrataAction.CREATE:
            self._errata_change_records.append(pu_ec_fn(type=ChangeType.CREATE))
        elif self.errata_action == ErrataAction.UPDATE:
            self._errata_change_records.append(pu_ec_fn(type=ChangeType.UPDATE))
        elif self.errata_action == ErrataAction.DISCARD:
            self._errata_change_records.append(pu_ec_fn(type=ChangeType.DISCARD))

        # add errata change history record for package update
        if self.bulletin_action == ErrataAction.CREATE:
            self._errata_change_records.append(bu_ec_fn(type=ChangeType.CREATE))
        elif self.bulletin_action == ErrataAction.UPDATE:
            self._errata_change_records.append(bu_ec_fn(type=ChangeType.UPDATE))
        elif self.bulletin_action == ErrataAction.DISCARD:
            self._errata_change_records.append(bu_ec_fn(type=ChangeType.DISCARD))
        # if no bulletin was registered: self.bulletin_action = ErrataAction.NONE

    def _handle_errata_create(self):
        if self.errata_action != ErrataAction.CREATE:
            raise ErrataManageError(
                f"Invalid errata change action: {self.errata_action.name}"
            )

        # build new errata
        _eid = register_package_update_id(
            self.eid_service, self._errata_update.year
        )
        new_errata = self._errata_update.errata.update(
            id=_eid.id, created=_eid.created, updated=_eid.updated
        )
        self._errata_update.new_eid = new_errata.id
        logger.info(f"Registered new ErrataID: {new_errata.id}")
        self._errata_history_records[ErrataType.PACKAGE] = new_errata

        # build or update related bulletin
        if self._bulletin_update is None:
            return

        if self.bulletin_action == ErrataAction.CREATE:
            new_bulletin = build_new_bulletin(
                eid_service=self.eid_service,
                branch_state=self._bulletin_update.branch,
                errata=new_errata,
            )
            self._bulletin_update.new_eid = new_bulletin.id
            logger.info(f"Registered new bulletin: {new_bulletin.id}")
        elif self.bulletin_action == ErrataAction.UPDATE:
            new_bulletin = update_bulletin_by_errata_add(
                eid_service=self.eid_service,
                bulletin=self._bulletin_update.errata,
                new_errata=new_errata,
            )
            self._bulletin_update.new_eid = new_bulletin.id
            logger.info(
                f"Bulletin has been updated: {self._bulletin_update.old_eid} -> {new_bulletin.id}"
            )
            # XXX: handle previously discarded bulletin
            if new_bulletin.is_discarded:
                new_bulletin = new_bulletin.update(is_discarded=False)
        else:
            err_message = (
                f"Bulletin action {self.bulletin_action.name} is not supported "
                f"for errata action {self.errata_action.name}"
            )
            logger.error(err_message)
            raise ErrataManageError(err_message)

        self._errata_history_records[ErrataType.BULLETIN] = new_bulletin

    def _handle_errata_update(self):
        if self.errata_action != ErrataAction.UPDATE:
            raise ErrataManageError(
                f"Invalid errata change action: {self.errata_action.name}"
            )

        # build new errata
        _eid = update_errata_id(self.eid_service, self._errata_update.errata.id.id)  # type: ignore
        new_errata = self._errata_update.errata.update(id=_eid.id, updated=_eid.updated)
        self._errata_update.new_eid = new_errata.id
        logger.info(f"Registered new ErrataID: {new_errata.id}")
        self._errata_history_records[ErrataType.PACKAGE] = new_errata

        # build or update related bulletin
        if self._bulletin_update is None:
            return

        if self.bulletin_action == ErrataAction.UPDATE:
            new_bulletin = update_bulletin_by_errata_update(
                eid_service=self.eid_service,
                bulletin=self._bulletin_update.errata,
                errata=self._errata_update.errata,
                new_errata=new_errata,
            )
            self._bulletin_update.new_eid = new_bulletin.id
            logger.info(
                f"Bulletin has been updated: {self._bulletin_update.old_eid} -> {new_bulletin.id}"
            )
        else:
            err_message = (
                f"Bulletin action {self.bulletin_action.name} is not supported "
                f"for errata action {self.errata_action.name}"
            )
            logger.error(err_message)
            raise ErrataManageError(err_message)

        self._errata_history_records[ErrataType.BULLETIN] = new_bulletin

    def _handle_errata_discard(self):
        if self.errata_action != ErrataAction.DISCARD:
            raise ErrataManageError(
                f"Invalid errata change action: {self.errata_action.name}"
            )

        # build new errata with 'is_discarded' set to True
        _eid = update_errata_id(self.eid_service, self._errata_update.errata.id.id)  # type: ignore
        new_errata = self._errata_update.errata.update(
            id=_eid.id, updated=_eid.updated, is_discarded=True
        )
        self._errata_update.new_eid = new_errata.id
        logger.info(f"Registered new ErrataID: {new_errata.id}")
        self._errata_history_records[ErrataType.PACKAGE] = new_errata

        # build or update related bulletin
        if self._bulletin_update is None:
            return

        elif self.bulletin_action == ErrataAction.UPDATE:
            new_bulletin = update_bulletin_by_errata_discard(
                eid_service=self.eid_service,
                bulletin=self._bulletin_update.errata,
                errata=self._errata_update.errata,
            )
            self._bulletin_update.new_eid = new_bulletin.id
            # change bulletin action if bulletin was not discarded
            if not new_bulletin.is_discarded:
                self._bulletin_update.action = ErrataAction.UPDATE
                logger.info(
                    f"Bulletin has been updated: {self._bulletin_update.old_eid} -> {new_bulletin.id}"
                )
            else:
                self._bulletin_update.action = ErrataAction.DISCARD
                logger.info(
                    f"Bulletin has been discarded: {self._bulletin_update.old_eid} -> {new_bulletin.id}"
                )
        else:
            err_message = (
                f"Bulletin action {self.bulletin_action.name} is not supported "
                f"for errata action {self.errata_action.name}"
            )
            logger.error(err_message)
            raise ErrataManageError(err_message)

        self._errata_history_records[ErrataType.BULLETIN] = new_bulletin
