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

from collections import defaultdict
from typing import Any

from altrepo_api.api.base import APIWorker, WorkerResult
from altrepo_api.api.misc import lut
from altrepo_api.libs.errata_server.errata_sa_service import (
    ErrataServerError,
    ErrataSAService,
    Errata as SaErrata,
    SaAction,
    UserInfo,
)
from altrepo_api.settings import namespace as settings
from altrepo_api.utils import get_logger, make_tmp_table_name, sort_branches

from ..dataclasses import ExcludedPackagesSchema, PackageScheme
from ..sql import sql


logger = get_logger(__name__)


def get_errata_service() -> ErrataSAService:
    try:
        return ErrataSAService(
            url=settings.ERRATA_MANAGE_URL,
            access_token="",
            user=UserInfo(name="", ip=""),
            dry_run=True,
        )
    except ErrataServerError as e:
        logger.error(f"Failed to connect to ErrataSA service: {e}")
        raise RuntimeError("error: %s" % e)


class VulnExcluded(APIWorker):
    """API worker for handling vulnerability exclusions."""

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def _get_cpe_hashes(self, conditions_cpe: set[str]) -> dict[str, int]:
        """Get CPE hashes."""

        if not conditions_cpe:
            return {}

        tmp_table = make_tmp_table_name("cpe_hashes")
        response = self.send_sql_request(
            self.sql.get_cpe_hash.format(tmp_table=tmp_table),
            external_tables=[
                {
                    "name": tmp_table,
                    "structure": [("cpm_cpe", "String")],
                    "data": [{"cpm_cpe": p} for p in conditions_cpe],
                }
            ],
        )
        return {el[0]: el[1] for el in response} if response else {}

    def _excluded_packages(
        self, vuln_id: str, conditions_pkgs: set[str], cpe_hashes: dict[str, int]
    ) -> list[ExcludedPackagesSchema]:
        """
        Query database for excluded packages matching the specified conditions.
        """

        # Build WHERE clause components
        conditions = []
        if conditions_pkgs:
            conditions.append(f"pkg_name IN {tuple(conditions_pkgs)}")
        if cpe_hashes:
            conditions.append(f"pkg_cpe_hash IN {tuple(cpe_hashes.values())}")

        where_clause = f" AND ({' OR '.join(conditions)})" if conditions else ""
        response = self.send_sql_request(
            self.sql.get_excluded_packages.format(
                vuln_id=vuln_id, where_clause=where_clause
            ),
        )

        if not response:
            return []
        return [ExcludedPackagesSchema(*row) for row in response]

    @staticmethod
    def _match_packages_with_errata(
        filtered_erratas: list[SaErrata],
        packages: list[ExcludedPackagesSchema],
        cpe_hashes: dict[str, int],
    ) -> list[dict[str, Any]]:
        """
        Match packages with corresponding errata records
        using multiple lookup strategies.
        """

        # create indexes for faster lookups
        pkg_name_index = defaultdict(list)
        cpe_index = defaultdict(list)
        cve_index = defaultdict(list)

        for pkg in packages:
            # index named package
            pkg_name_index[pkg.name].append(pkg)

            # index CPE
            if pkg.cpe and (cpe_key := cpe_hashes.get(pkg.cpe)):
                cpe_index[cpe_key].append(pkg)

            # index CVE
            if pkg.vuln_id:
                cve_index[pkg.vuln_id].append(pkg)

        # match errata with packages
        matched_data: list = []
        seen_pairs = set()
        for errata in filtered_erratas:
            eh = errata.eh
            if not eh.json:
                continue

            # try to match by CPE first
            if eh.json.action == SaAction.CPE and eh.json.vuln_cpe:
                cpe_key = cpe_hashes.get(eh.json.vuln_cpe, "")
                matched_packages: list[ExcludedPackagesSchema] = cpe_index.get(
                    cpe_key, []
                )

            # try to match by package name
            elif eh.json.action == SaAction.PACKAGE and eh.json.pkg_name:
                matched_packages: list[ExcludedPackagesSchema] = pkg_name_index.get(
                    eh.json.pkg_name, []
                )

            # fall back to matching by vulnerability ID
            else:
                matched_packages: list[ExcludedPackagesSchema] = cve_index.get(
                    eh.json.vuln_id, []
                )

            # create result entries for matched packages
            for pkg in [
                match
                for br in sort_branches(lut.known_branches)
                for match in matched_packages
                if br == match.branch
            ]:
                unique_key = (pkg.pkghash, eh.id)
                if unique_key not in seen_pairs:
                    seen_pairs.add(unique_key)
                    matched_data.append(
                        PackageScheme(
                            pkghash=pkg.pkghash,
                            name=pkg.name,
                            branch=pkg.branch,
                            version=pkg.version,
                            release=pkg.release,
                            errata_id=eh.id,
                            task_id=eh.task_id,
                            subtask_id=eh.subtask_id,
                            task_state=eh.task_state,
                        ).asdict()
                    )
        return matched_data

    @staticmethod
    def _build_conditions(
        filtered_erratas: list[SaErrata],
    ) -> tuple[set[str], set[str]]:
        """Extract CPE and package conditions from errata."""
        conditions_cpe = set()
        conditions_pkgs = set()

        for errata in filtered_erratas:
            if not errata.eh.json:
                continue
            json = errata.eh.json
            if json.action == SaAction.CPE and json.vuln_cpe:
                conditions_cpe.add(json.vuln_cpe)
            elif json.action == SaAction.PACKAGE and json.pkg_name:
                conditions_pkgs.add(json.pkg_name)

        return conditions_cpe, conditions_pkgs

    def get(self) -> WorkerResult:
        vuln_id = self.args["vuln_id"]

        # initialize errata service in dry-run mode
        service = get_errata_service()
        try:
            erratas = service.list()
        except ErrataServerError as e:
            status_code = e.status_code if e.status_code else 500
            return self.store_error(
                {"message": f"Failed to get records from Errata Server: {e}"},
                severity=self.LL.ERROR,
                http_code=status_code,
            )

        def is_relevant_errata(errata: SaErrata) -> bool:
            # skip discarded records
            if errata.is_discarded:
                return False

            # check if the errata matches our vulnerability ID
            if errata.eh.json is None or errata.eh.json.vuln_id != vuln_id:
                return False

            return True

        # filter errata records
        filtered_erratas = [e for e in erratas if is_relevant_errata(e)]
        if not filtered_erratas:
            return self.store_error({"message": f"No data found in DB for {self.args}"})

        # process conditions and query packages
        conditions_cpe, conditions_pkgs = self._build_conditions(filtered_erratas)
        cpe_hashes = self._get_cpe_hashes(conditions_cpe)
        packages = self._excluded_packages(vuln_id, conditions_pkgs, cpe_hashes)
        if not packages:
            return self.store_error({"message": f"No data found in DB for {self.args}"})

        matched_data = self._match_packages_with_errata(
            filtered_erratas=filtered_erratas, packages=packages, cpe_hashes=cpe_hashes
        )
        res = {
            "request_args": self.args,
            "length": len(packages),
            "packages": matched_data,
        }
        return res, 200
