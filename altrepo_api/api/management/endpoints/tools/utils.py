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

import re

from datetime import datetime

from altrepo_api.utils import get_logger

from .constants import (
    DT_NEVER,
    ERRATA_CHANGE_ACTIONS,
    ERRATA_VALID_SOURCES,
    ERRATA_VALID_TYPES,
)

logger = get_logger(__name__)
re_errata_id = re.compile(r"^ALT-[A-Z]+-2\d{3}-\d{4,}-\d{1,}$")


def validate_action(action: str) -> bool:
    return action in ERRATA_CHANGE_ACTIONS


def validate_type(value: str) -> bool:
    return value in ERRATA_VALID_TYPES


def validate_source(value: str) -> bool:
    return value in ERRATA_VALID_SOURCES


def dt_from_iso(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value)
    except (TypeError, ValueError):
        logger.warning(f"Failed to parse datetime: {value}")
        return DT_NEVER
