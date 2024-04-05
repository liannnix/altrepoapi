# ALTRepo API
# Copyright (C) 2021-2024  BaseALT Ltd

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

from datetime import datetime
from random import randint
from typing import Optional, Protocol

from altrepo_api.api.misc import lut
from altrepo_api.settings import namespace
from altrepo_api.libs.errata_service import (
    ErrataIDService,
    ErrataIDServiceError,
    ErrataIDServiceResult,
)
from altrepo_api.utils import get_logger

from .base import ErrataID, ErrataManageError
from .constants import DT_NEVER

logger = get_logger(__name__)


class ErrataIDServiceProtocol(Protocol):
    def __init__(self, url: str) -> None: ...

    def register(self, prefix: str, year: Optional[int]) -> ErrataIDServiceResult: ...

    def check(self, id: str) -> ErrataIDServiceResult: ...

    def update(self, id: str) -> ErrataIDServiceResult: ...

    def discard(self, id: str) -> ErrataIDServiceResult: ...


class stubErrataIDService:
    def __init__(self, url: str) -> None:
        self.eid = ErrataIDService(url)
        # XXX: double `randint` gives a little bit less repetitions
        self.counter = randint(0, 9) * 100 + randint(0, 9) * 10

    @property
    def count(self):
        self.counter += 1
        return self.counter

    def register(self, prefix: str, year: Optional[int]) -> ErrataIDServiceResult:
        dt = datetime.now()
        _year = year if year is not None else dt.year
        id = f"{prefix}-{_year}-{self.count:04d}-1"
        logger.info(f"DRY_RUN: Registered new Errata ID {id}")
        return ErrataIDServiceResult(id, dt, dt)

    def check(self, id: str) -> ErrataIDServiceResult:
        return self.eid.check(id)

    def update(self, id: str) -> ErrataIDServiceResult:
        dt = datetime.now()
        parts = id.split("-")
        v = str(int(parts[-1]) + 1)
        _id = "-".join(parts[:-1] + [v])
        logger.info(f"DRY_RUN: Updated Errata ID {id} -> {_id}")
        return ErrataIDServiceResult(_id, DT_NEVER, dt)

    def discard(self, id: str) -> ErrataIDServiceResult:
        dt = datetime.now()
        return ErrataIDServiceResult(id, DT_NEVER, dt)


def get_errataid_service(dry_run: bool) -> ErrataIDServiceProtocol:
    """Returns ErrataID service interface class instance using URL from API
    configuration namespace."""

    Service = stubErrataIDService if dry_run else ErrataIDService

    try:
        return Service(url=namespace.ERRATA_ID_URL)
    except ErrataIDServiceError as e:
        logger.error(f"Failed to connect to ErrataID service: {e}")
        raise ErrataManageError("error: %s" % e)


def _check_errata_id(
    eid_service: ErrataIDServiceProtocol, id: str
) -> ErrataIDServiceResult:
    try:
        logger.info(f"Check errata ID latest version for {id}")
        return eid_service.check(id)
    except ErrataIDServiceError as e:
        logger.error(f"Failed to update errata ID version for {id}: {e}")
        raise ErrataManageError("error: %s" % e)


def check_errata_id(eid_service: ErrataIDServiceProtocol, eid: ErrataID) -> ErrataID:
    """Returns latest errata id version from ErrataID service."""
    return ErrataID.from_id(_check_errata_id(eid_service, eid.id).id)


def _reister_errata_id(
    eid_service: ErrataIDServiceProtocol, prefix: str, year: Optional[int]
) -> ErrataIDServiceResult:
    try:
        logger.info(f"Register new errata ID for {prefix}-{year}")
        return eid_service.register(prefix=prefix, year=year)
    except ErrataIDServiceError as e:
        logger.error(f"Failed to register new errata ID for {prefix}-{year}: {e}")
        raise ErrataManageError("error: %s" % e)


def register_package_update_id(
    eid_service: ErrataIDServiceProtocol, year: int
) -> ErrataIDServiceResult:
    """Registers new package update identificator in ErrataID service."""
    return _reister_errata_id(
        eid_service=eid_service, prefix=lut.errata_package_update_prefix, year=year
    )


def register_branch_update_id(
    eid_service: ErrataIDServiceProtocol, year: int
) -> ErrataIDServiceResult:
    """Registers new branch update identificator in ErrataID service."""
    return _reister_errata_id(
        eid_service=eid_service, prefix=lut.errata_branch_update_prefix, year=year
    )


def register_errata_change_id(
    eid_service: ErrataIDServiceProtocol,
) -> ErrataIDServiceResult:
    """Registers new errata change identificator in ErrataID service."""
    return _reister_errata_id(
        eid_service=eid_service, prefix=lut.errata_change_prefix, year=None
    )


def update_errata_id(
    eid_service: ErrataIDServiceProtocol, id: str
) -> ErrataIDServiceResult:
    """Updates errata identificator version in ErrataID service in a failsafe manner."""

    check_id = _check_errata_id(eid_service, id)
    # if Errata ID version is inconsistent with one from DB - use the latest one
    if check_id.id != id:
        logger.warning(
            f"Failed to update version of errata ID {id}. "
            f"Will use the latest one: {check_id.id}"
        )
        id = check_id.id

    try:
        logger.info(f"Update errata identificator version for {id}")
        return eid_service.update(id)
    except ErrataIDServiceError as e:
        logger.error(f"Failed to update errata ID version for {id}: {e}")
        raise ErrataManageError("error: %s" % e)


def discard_errata_id(
    eid_service: ErrataIDServiceProtocol, id: str
) -> ErrataIDServiceResult:
    """Discards errata identificator in ErrataID service."""

    try:
        logger.info(f"Discrad errata identificator version for {id}")
        return eid_service.discard(id)
    except ErrataIDServiceError as e:
        logger.error(f"Failed to discard errata ID version for {id}: {e}")
        raise ErrataManageError("error: %s" % e)
