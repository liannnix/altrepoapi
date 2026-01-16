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

from altrepo_api.api.base import APIWorker
from altrepo_api.api.maintainer_score_config import config
from ..sql import sql


class MaintainerScoresBatch(APIWorker):
    """Calculate maintainer scores for all packages in a branch."""

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def get(self):
        branch = self.args["branch"]

        # Build SQL parameters with config values
        sql_params = {
            "branch": branch,
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
                self.sql.get_maintainer_scores_batch,
                sql_params,
            )
        )
        if not self.sql_status:
            return self.error

        # Query 2: Bugzilla-based scores
        bugfix_response = self.send_sql_request(
            (
                self.sql.get_maintainer_bugfixes_batch,
                sql_params,
            )
        )
        # Build bugfix lookup: {(pkg_name, nick): {bugfix_score, bugfix_count, recent_bugfixes}}
        bugfix_data = {}
        if self.sql_status and bugfix_response:
            for row in bugfix_response:
                key = (row[0], row[1])  # (pkg_name, nick)
                bugfix_data[key] = {
                    "bugfix_score": row[2],
                    "bugfix_count": row[3],
                    "recent_bugfixes": row[4],
                }

        # Group changelog rows by package name
        # SQL returns: pkg_name, nick, score, updates, patches, nmu_count, in_acl, last_activity, recent_commits
        packages_dict = {}
        for row in response:
            pkg_name = row[0]
            nick = row[1]
            if pkg_name not in packages_dict:
                packages_dict[pkg_name] = []
            packages_dict[pkg_name].append(
                {
                    "nick": nick,
                    "changelog_score": row[2],
                    "updates": row[3],
                    "patches": row[4],
                    "nmu": row[5],
                    "in_acl": bool(row[6]),
                    "last_activity": row[7],
                    "recent_commits": row[8],
                }
            )

        # Build response with bonuses applied
        packages = []
        for pkg_name, maintainer_data in packages_dict.items():
            # Find last committer for this package
            last_committer = max(maintainer_data, key=lambda x: x["last_activity"])[
                "nick"
            ]

            maintainers = []
            for md in maintainer_data:
                nick = md["nick"]
                changelog_score = md["changelog_score"]
                recent_commits = md["recent_commits"]

                # Get bugfix data
                bf = bugfix_data.get((pkg_name, nick), {})
                bugfix_score = bf.get("bugfix_score", 0)
                bugfix_count = bf.get("bugfix_count", 0)
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
                        "updates": md["updates"],
                        "patches": md["patches"],
                        "nmu": md["nmu"],
                        "bugfixes": bugfix_count,
                        "in_acl": md["in_acl"],
                        "last_activity": (
                            md["last_activity"].strftime("%Y-%m-%d")
                            if md["last_activity"]
                            else None
                        ),
                        "recent_commits": recent_commits,
                        "bonus_applied": bonus_applied,
                    }
                )

            # Re-sort by final score
            maintainers.sort(key=lambda x: x["score"], reverse=True)

            top_score = maintainers[0]["score"] if maintainers else 0
            if top_score >= config.ACTIVE_THRESHOLD:
                status = "active"
            elif top_score >= config.LOW_ACTIVITY_THRESHOLD:
                status = "low_activity"
            else:
                status = "orphaned"

            primary = maintainers[0]["nick"] if maintainers and top_score > 0 else None

            packages.append(
                {
                    "package": pkg_name,
                    "primary_maintainer": primary,
                    "status": status,
                    "maintainers": maintainers,
                }
            )

        return {
            "request_args": self.args,
            "branch": branch,
            "length": len(packages),
            "packages": packages,
        }, 200
