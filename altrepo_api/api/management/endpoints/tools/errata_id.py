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

from typing import Optional

from altrepo_api.api.misc import lut
from altrepo_api.settings import namespace
from altrepo_api.libs.errata_service import (
    ErrataIDService,
    ErrataIDServiceError,
    ErrataIDServiceResult,
)
from altrepo_api.utils import get_logger

from .base import ErrataID, ErrataManageError

logger = get_logger(__name__)


def get_errataid_service() -> ErrataIDService:
    try:
        return ErrataIDService(url=namespace.ERRATA_ID_URL)
    except ErrataIDServiceError as e:
        logger.error(f"Failed to connect to ErrataID service: {e}")
        raise ErrataManageError("error: %s" % e)


def _check_errata_id(eid_service: ErrataIDService, id: str) -> ErrataIDServiceResult:
    try:
        logger.debug(f"Check errata ID latest version for {id}")
        return eid_service.check(id)
    except ErrataIDServiceError as e:
        logger.error(f"Failed to update errata ID version for {id}: {e}")
        raise ErrataManageError("error: %s" % e)


def check_errata_id(eid_service: ErrataIDService, eid: ErrataID) -> ErrataID:
    return ErrataID.from_id(_check_errata_id(eid_service, eid.id).id)


def _reister_errata_id(
    eid_service: ErrataIDService, prefix: str, year: Optional[int]
) -> ErrataIDServiceResult:
    try:
        logger.debug(f"Register new errata ID for {prefix}-{year}")
        return eid_service.register(prefix=prefix, year=year)
    except ErrataIDServiceError as e:
        logger.error(f"Failed to register new errata ID for {prefix}-{year}: {e}")
        raise ErrataManageError("error: %s" % e)


def register_package_update_id(
    eid_service: ErrataIDService, year: int
) -> ErrataIDServiceResult:
    return _reister_errata_id(
        eid_service=eid_service, prefix=lut.errata_package_update_prefix, year=year
    )


def register_branch_update_id(
    eid_service: ErrataIDService, year: int
) -> ErrataIDServiceResult:
    return _reister_errata_id(
        eid_service=eid_service, prefix=lut.errata_branch_update_prefix, year=year
    )


def register_errata_change_id(eid_service: ErrataIDService) -> ErrataIDServiceResult:
    return _reister_errata_id(
        eid_service=eid_service, prefix=lut.errata_change_prefix, year=None
    )


def update_errata_id(eid_service: ErrataIDService, id: str) -> ErrataIDServiceResult:
    try:
        logger.debug(f"Update errata ID version for {id}")
        return eid_service.update(id)
    except ErrataIDServiceError as e:
        logger.error(f"Failed to update errata ID version for {id}: {e}")
        raise ErrataManageError("error: %s" % e)
