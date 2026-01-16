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

"""
Maintainer Score Algorithm Configuration.

This module contains all coefficients and thresholds used in the maintainer
score calculation algorithm. Both single-package and batch endpoints use
these same settings to ensure consistent scoring.

Score Formula:
    base_score = changelog_score + bugfix_score

    changelog_score = sum(weight * decay * acl_factor)
        where:
        - weight = W_UPDATE (alt1), W_PATCH (other), or W_NMU (NMU without ACL)
        - decay = exp(-age_days * ln(2) / HALF_LIFE_DAYS)
        - acl_factor = 1.0 if in_acl else ACL_NON_MEMBER_FACTOR

    bugfix_score = sum(W_BUGFIX * decay)
        for each resolved/fixed bug in Bugzilla

    final_score = base_score * RECENT_MAINTAINER_BONUS
        if maintainer has recent activity AND is last committer
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class MaintainerScoreConfig:
    # fmt: off
    # Score weights for different contribution types
    W_UPDATE: float = 3.0      # Weight for version updates (alt1, 0.x releases)
    W_PATCH: float = 1.5       # Weight for patches/fixes (alt2+)
    W_BUGFIX: float = 4.0      # Weight for Bugzilla bug fixes
    W_NMU: float = 0.0         # Weight for NMU uploads (non-maintainer)

    # Time decay settings
    HALF_LIFE_DAYS: int = 730  # Score half-life in days (2 years)

    # ACL factor for non-members
    ACL_NON_MEMBER_FACTOR: float = 0.5  # Score multiplier for non-ACL members

    # Recent activity bonus settings
    RECENT_MAINTAINER_BONUS: float = 2.5  # Multiplier for active maintainers
    RECENT_PERIOD_DAYS: int = 180         # Period to consider "recent" (6 months)
    MIN_RECENT_COMMITS: int = 3           # Min commits for bonus eligibility
    MIN_RECENT_BUGFIXES: int = 1          # Min bugfixes for bonus eligibility

    # Package status thresholds (based on top maintainer score)
    ACTIVE_THRESHOLD: float = 1.0         # Score >= this = "active"
    LOW_ACTIVITY_THRESHOLD: float = 0.3   # Score >= this = "low_activity"
    # Score < LOW_ACTIVITY_THRESHOLD = "orphaned"
    # fmt: on


# Singleton instance for use throughout the application
config = MaintainerScoreConfig()
