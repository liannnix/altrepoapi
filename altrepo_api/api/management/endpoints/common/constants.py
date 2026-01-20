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

from altrepo_api.api.misc import lut


ERRAT_CHANGE_ACTOR_DEFAULT = "Errata management API"

DRY_RUN_KEY = "dry_run"
CHANGE_SOURCE_KEY = "change_source"
CHANGE_SOURCE_AUTO = "auto"
CHANGE_SOURCE_MANUAL = "manual"


BDU_ID_TYPE = "BDU"
BDU_ID_PREFIX = f"{BDU_ID_TYPE}:"
CVE_ID_TYPE = "CVE"
CVE_ID_PREFIX = f"{CVE_ID_TYPE}-"
GHSA_ID_TYPE = "GHSA"
GHSA_ID_PREFIX = f"{GHSA_ID_TYPE}-"
MFSA_ID_TYPE = "MFSA"
MFSA_ID_PREFIX = f"{MFSA_ID_TYPE}"
OVE_ID_TYPE = "OVE"
OVE_ID_PREFIX = f"{OVE_ID_TYPE}-"
BUG_ID_TYPE = "BUG"
BUG_ID_PREFIX = ""

VULN_ID_TYPE2PREFIX = {
    BDU_ID_TYPE: BDU_ID_PREFIX,
    CVE_ID_TYPE: CVE_ID_PREFIX,
    GHSA_ID_TYPE: GHSA_ID_PREFIX,
    MFSA_ID_TYPE: MFSA_ID_PREFIX,
    OVE_ID_TYPE: OVE_ID_PREFIX,
    BUG_ID_TYPE: BUG_ID_PREFIX,
}

ERRATA_PACKAGE_UPDATE_PREFIX = f"{lut.errata_package_update_prefix}-"
ERRATA_BRANCH_BULLETIN_PREFIX = f"{lut.errata_branch_update_prefix}-"
ERRATA_CHNAGE_PREFIX = f"{lut.errata_change_prefix}-"

TASK_STATE_DONE = "DONE"

CHANGE_ACTION_CREATE = "create"
CHANGE_ACTION_DISCARD = "discard"
CHANGE_ACTION_UPDATE = "update"
CHANGE_ACTIONS = (CHANGE_ACTION_CREATE, CHANGE_ACTION_DISCARD, CHANGE_ACTION_UPDATE)

BRANCH_PACKAGE_ERRATA_TYPE = "branch"
BRANCH_PACKAGE_ERRATA_SOURCE = "changelog"
TASK_PACKAGE_ERRATA_TYPE = "task"
TASK_PACKAGE_ERRATA_SOURCE = "changelog"


ERRATA_PACKAGE_UPDATE_SOURCES = (
    BRANCH_PACKAGE_ERRATA_SOURCE,
    TASK_PACKAGE_ERRATA_SOURCE,
)
ERRATA_PACKAGE_UPDATE_TYPES = (BRANCH_PACKAGE_ERRATA_TYPE, TASK_PACKAGE_ERRATA_TYPE)

SUPPORTED_BRANCHES_WITH_TASKS = lut.errata_manage_branches_with_tasks
SUPPORTED_BRANCHES_WITHOUT_TASKS = lut.errata_manage_branches_without_tasks
SUPPORTED_BRANCHES = (*SUPPORTED_BRANCHES_WITH_TASKS, *SUPPORTED_BRANCHES_WITHOUT_TASKS)

PNC_STATE_ACTIVE = "active"
PNC_STATE_INACTIVE = "inactive"
PNC_STATE_CANDIDATE = "candidate"
PNC_STATES = (PNC_STATE_ACTIVE, PNC_STATE_INACTIVE, PNC_STATE_CANDIDATE)
PNC_SOURCES = (CHANGE_SOURCE_AUTO, CHANGE_SOURCE_MANUAL)

COMMENT_ENTITY_TYPES = lut.comment_ref_types

DEFAULT_REASON_SOURCE_TYPES = lut.default_reason_source_types

DEFAULT_REASON_ACTION_TYPES = (
    CHANGE_ACTION_CREATE,
    CHANGE_ACTION_DISCARD,
    CHANGE_ACTION_UPDATE,
)
