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

from datetime import datetime, timezone
from typing import Optional

from altrepo_api.utils import get_logger
from altrepo_api.api.parser import bug_id_type

from .base import Reference
from .constants import (
    COMMENT_ENTITY_TYPES,
    DT_NEVER,
    CHANGE_ACTIONS,
    ERRATA_VALID_SOURCES,
    ERRATA_VALID_TYPES,
    SUPPORTED_BRANCHES,
    SUPPORTED_BRANCHES_WITH_TASKS,
    SUPPORTED_BRANCHES_WITHOUT_TASKS,
    BDU_ID_TYPE,
    CVE_ID_TYPE,
    GHSA_ID_TYPE,
    MFSA_ID_TYPE,
    OVE_ID_TYPE,
    BUG_ID_TYPE,
    DEFAULT_REASON_SOURCE_TYPES,
    DEFAULT_REASON_ACTION_TYPES,
)

logger = get_logger(__name__)

re_errata_id = re.compile(r"^ALT-[A-Z]+-2\d{3}-\d{4,}-\d{1,}$")
re_cve_id = re.compile(r"^CVE-\d{4}-\d{4,}$", re.IGNORECASE)
re_ghsa_id = re.compile(r"^GHSA(-[23456789cfghjmpqrvwx]{4}){3}$")
re_bdu_id = re.compile(r"^BDU:\d{4}-\d{5}$", re.IGNORECASE)
re_mfsa_id = re.compile(r"^MFSA[- ]+\d{4}-\d{2}$", re.IGNORECASE)
re_ove_id = re.compile(r"^OVE-\d{8}-\d{4}$", re.IGNORECASE)
re_bug_id = re.compile(r"^\d{4,}$")

VULN_ID_REGEXS = (
    (BDU_ID_TYPE, re_bdu_id),
    (CVE_ID_TYPE, re_cve_id),
    (GHSA_ID_TYPE, re_ghsa_id),
    (MFSA_ID_TYPE, re_mfsa_id),
    (OVE_ID_TYPE, re_ove_id),
    (BUG_ID_TYPE, re_bug_id),
)

_TZ_UTC = timezone.utc
_TZ_LOCAL = datetime.now().astimezone(None).tzinfo


def validate_action(action: str) -> bool:
    return action in CHANGE_ACTIONS


def validate_type(value: str) -> bool:
    return value in ERRATA_VALID_TYPES


def validate_source(value: str) -> bool:
    return value in ERRATA_VALID_SOURCES


def validate_branch(branch: str) -> bool:
    return branch in SUPPORTED_BRANCHES


def validate_branch_with_tasks(branch: str) -> bool:
    return branch in SUPPORTED_BRANCHES_WITH_TASKS


def validate_branch_without_tasks(branch: str) -> bool:
    return branch in SUPPORTED_BRANCHES_WITHOUT_TASKS


def validate_comment_entity_type(type: str) -> bool:
    return type in COMMENT_ENTITY_TYPES


def validate_default_reason_source(source: str) -> bool:
    return source in DEFAULT_REASON_SOURCE_TYPES


def validate_default_reason_action(action: str) -> bool:
    return action in DEFAULT_REASON_ACTION_TYPES


def convert_dt_to_timezone_aware(dt: datetime) -> datetime:
    """Checks if datetime object is timezone aware.
    Converts timezone naive datetime to aware one assuming timezone is
    equal to local one for API host."""

    if dt.tzinfo is not None and dt.tzinfo.utcoffset is not None:
        # datetime object is timezone aware
        return dt

    # datetime object is timezone naive
    return dt.replace(tzinfo=_TZ_LOCAL).astimezone(_TZ_UTC)


def dt_from_iso(value: str) -> datetime:
    try:
        return convert_dt_to_timezone_aware(datetime.fromisoformat(value))
    except (TypeError, ValueError):
        logger.warning(f"Failed to parse datetime: {value}")
        return DT_NEVER


def parse_vuln_id(vuln_id: str) -> Optional[Reference]:
    """Validates a vulnerability ID against known types and returns a Reference object
    if valid, otherwise returns None."""

    def vulnid2reftype(id: str) -> Reference:
        for type_, regex in VULN_ID_REGEXS:
            if regex.fullmatch(id) is not None:
                return Reference(type=type_, link=id)
        raise ValueError(f"Invalid vulnerability identifier: {id}")

    try:
        ref = vulnid2reftype(vuln_id)
        if ref.type == BUG_ID_TYPE:
            _ = bug_id_type(ref.link)
    except ValueError:
        return None

    return ref
