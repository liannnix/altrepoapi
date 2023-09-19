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

from datetime import datetime, timezone

from altrepo_api.api.misc import lut

DT_NEVER = datetime.fromtimestamp(0).replace(tzinfo=timezone.utc)

BDU_ID_TYPE = "BDU"
BDU_ID_PREFIX = f"{BDU_ID_TYPE}:"
CVE_ID_TYPE = "CVE"
CVE_ID_PREFIX = f"{CVE_ID_TYPE}-"

ERRATA_PACKAGE_UPDATE_PREFIX = f"{lut.errata_package_update_prefix}-"
ERRATA_BRANCH_BULLETIN_PREFIX = f"{lut.errata_branch_update_prefix}-"
ERRATA_CHNAGE_PREFIX = f"{lut.errata_change_prefix}-"

TASK_STATE_DONE = "DONE"

ERRATA_CHANGE_ACTION_CREATE = "create"
ERRATA_CHANGE_ACTION_DISCARD = "discard"
ERRATA_CHANGE_ACTION_UPDATE = "update"
ERRATA_CHANGE_ACTIONS = (
    ERRATA_CHANGE_ACTION_CREATE,
    ERRATA_CHANGE_ACTION_DISCARD,
    ERRATA_CHANGE_ACTION_UPDATE,
)

BRANCH_BULLETIN_ERRATA_SOURCE = "branch"
BRANCH_BULLETIN_ERRATA_TYPE = "bulletin"
BRANCH_PACKAGE_ERRATA_TYPE = "branch"
BRANCH_PACKAGE_ERRATA_SOURCE = "changelog"
TASK_PACKAGE_ERRATA_TYPE = "task"
TASK_PACKAGE_ERRATA_SOURCE = "changelog"

ERRATA_VALID_TYPES = (
    BRANCH_BULLETIN_ERRATA_TYPE,
    BRANCH_PACKAGE_ERRATA_TYPE,
    TASK_PACKAGE_ERRATA_TYPE,
)
ERRATA_VALID_SOURCES = (
    BRANCH_BULLETIN_ERRATA_SOURCE,
    BRANCH_PACKAGE_ERRATA_SOURCE,
    TASK_PACKAGE_ERRATA_SOURCE,
)

ERRATA_PACKAGE_UPDATE_SOURCES = (
    BRANCH_PACKAGE_ERRATA_SOURCE,
    TASK_PACKAGE_ERRATA_SOURCE,
)
ERRATA_PACKAGE_UPDATE_TYPES = (BRANCH_PACKAGE_ERRATA_TYPE, TASK_PACKAGE_ERRATA_TYPE)
