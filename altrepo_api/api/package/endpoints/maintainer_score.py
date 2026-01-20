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

from altrepo_api.api.base import APIWorker
from altrepo_api.api.maintainer_score_config import config
from ..sql import sql


class MaintainerScore(APIWorker):
    """Calculate maintainer scores for a package based on changelog activity."""

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def get(self):
        branch = self.args["branch"]
        package = self.args["name"]

        # Build SQL parameters with config values
        sql_params = {
            "branch": branch,
            "package": package,
            "half_life_days": config.HALF_LIFE_DAYS,
            "w_update": config.W_UPDATE,
            "w_patch": config.W_PATCH,
            "w_bugfix": config.W_BUGFIX,
            "w_nmu": config.W_NMU,
            "acl_non_member_factor": config.ACL_NON_MEMBER_FACTOR,
            "recent_period_days": config.RECENT_PERIOD_DAYS,
        }

        # Query 1: Changelog-based scores
        response = self.send_sql_request(
            (
                self.sql.get_maintainer_score,
                sql_params,
            )
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {
                    "message": "No changelog data found for package",
                    "args": self.args,
                }
            )

        # Query 2: Bugzilla-based scores
        bugfix_response = self.send_sql_request(
            (
                self.sql.get_maintainer_bugfixes,
                sql_params,
            )
        )
        bugfix_data = {}
        if self.sql_status and bugfix_response:
            for row in bugfix_response:
                bugfix_data[row[0]] = {
                    "bugfix_score": row[1],
                    "bugfix_count": row[2],
                    "bugfix_with_update": row[3],
                    "recent_bugfixes": row[4],
                    "last_bugfix": row[5],
                }

        # Parse changelog data
        # SQL returns: nick, score, updates, patches, nmu_count, in_acl, last_activity, recent_commits
        changelog_data = []
        for row in response:
            changelog_data.append(
                {
                    "nick": row[0],
                    "changelog_score": row[1],
                    "updates": row[2],
                    "patches": row[3],
                    "nmu": row[4],
                    "in_acl": bool(row[5]),
                    "last_activity": row[6],
                    "recent_commits": row[7],
                }
            )

        # Find who made the last commit (for bonus calculation)
        last_committer = max(changelog_data, key=lambda x: x["last_activity"])["nick"]

        # Build maintainers list with combined scores
        maintainers = []
        for cd in changelog_data:
            nick = cd["nick"]
            changelog_score = cd["changelog_score"]
            recent_commits = cd["recent_commits"]

            # Get bugfix data for this maintainer
            bf = bugfix_data.get(nick, {})
            bugfix_score = bf.get("bugfix_score", 0)
            bugfix_count = bf.get("bugfix_count", 0)
            bugfix_with_update = bf.get("bugfix_with_update", 0)
            recent_bugfixes = bf.get("recent_bugfixes", 0)

            # Base score = changelog + bugfix
            base_score = changelog_score + bugfix_score

            # Apply recent maintainer bonus if:
            # - Has at least MIN_RECENT_BUGFIXES bugfix OR MIN_RECENT_COMMITS commits
            # - AND is the last committer
            has_recent_activity = (
                recent_bugfixes >= config.MIN_RECENT_BUGFIXES
                or recent_commits >= config.MIN_RECENT_COMMITS
            )
            is_last_committer = nick == last_committer

            if has_recent_activity and is_last_committer:
                final_score = base_score * config.RECENT_MAINTAINER_BONUS
                bonus_applied = True
            else:
                final_score = base_score
                bonus_applied = False

            maintainers.append(
                {
                    "nick": nick,
                    "score": round(final_score, 2),
                    "base_score": round(base_score, 2),
                    "updates": cd["updates"],
                    "patches": cd["patches"],
                    "nmu": cd["nmu"],
                    "bugfixes": bugfix_count,
                    "bugfixes_with_update": bugfix_with_update,
                    "in_acl": cd["in_acl"],
                    "last_activity": (
                        cd["last_activity"].strftime("%Y-%m-%d")
                        if cd["last_activity"]
                        else None
                    ),
                    "recent_commits": recent_commits,
                    "bonus_applied": bonus_applied,
                }
            )

        # Re-sort by final score
        maintainers.sort(key=lambda x: x["score"], reverse=True)

        # Determine package status based on top score
        top_score = maintainers[0]["score"] if maintainers else 0
        if top_score >= config.ACTIVE_THRESHOLD:
            status = "active"
        elif top_score >= config.LOW_ACTIVITY_THRESHOLD:
            status = "low_activity"
        else:
            status = "orphaned"

        primary = maintainers[0]["nick"] if maintainers and top_score > 0 else None

        return {
            "request_args": self.args,
            "package": package,
            "branch": branch,
            "primary_maintainer": primary,
            "status": status,
            "maintainers": maintainers,
        }, 200
