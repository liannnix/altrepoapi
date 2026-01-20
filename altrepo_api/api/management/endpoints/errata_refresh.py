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
from collections import defaultdict
from typing import Iterable
from uuid import UUID

from altrepo_api.api.base import APIWorker, WorkerResult
from altrepo_api.libs.errata_server.errata_refresh_service import (
    ErrataRefreshService,
    ReferencesPatch,
)
from altrepo_api.libs.errata_server.errata_sa_service import (
    ErrataHistory,
    Reference,
    UserInfo,
)
from altrepo_api.settings import namespace as settings
from altrepo_api.utils import get_real_ip, make_tmp_table_name

from ..sql import sql
from .common.constants import CVE_ID_PREFIX

ErrataWithPatch = tuple[ErrataHistory, ReferencesPatch]
CpeMatch = tuple[str, str, bool, bool]
CpeTriplet = tuple[str, str, str]


def unescape(x: str) -> str:
    def first_pass(s: str) -> str:
        escaped = False
        current = ""

        for char in s:
            if escaped:
                current += char
                escaped = False
            elif char == "\\":
                escaped = True
            else:
                current += char

        return current

    x_ = first_pass(x)
    if not re.search(r"\\\W", x_):
        return x_
    else:
        return x_.replace("\\", "")


def escape(x: str):
    return re.sub(r":", r"\:", x)


def parse_cpe(cpe_str: str) -> CpeTriplet:
    parts = re.split(r"(?<!\\):", cpe_str)

    if len(parts) != 13:
        raise ValueError(f"Failed to parse CPE from {cpe_str}")

    return unescape(parts[3]), unescape(parts[4]), unescape(parts[10])


def cpe_triplet_to_str(cpe_triplet: CpeTriplet) -> str:
    return "cpe:2.3:a:{vendor}:{product}:*:*:*:*:*:{target_sw}:*:*".format(
        vendor=escape(cpe_triplet[0]),
        product=escape(cpe_triplet[1]),
        target_sw=escape(cpe_triplet[2]),
    )


def revert_patch(errata: ErrataHistory, patch: ReferencesPatch) -> ErrataHistory:
    return errata._replace(
        references=sorted(
            set(errata.references)
            .difference(set(patch.add_bugs).union(patch.add_vulns))
            .union(set(patch.del_bugs).union(patch.del_vulns)),
        ),
    )


class ErrataRefreshAnalyze(APIWorker):
    def __init__(self, connection, **kwargs) -> None:
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def check_params(self) -> bool:
        self.logger.debug(f"args : {self.args}")

        self.user = self.user = UserInfo(
            name=self.args["user"],
            ip=get_real_ip(),
        )

        return True

    def get_suspicious_changes_from_errata_server(
        self,
    ) -> Iterable[tuple[ErrataHistory, ReferencesPatch]]:
        self.status = False

        try:
            service = ErrataRefreshService(
                url=settings.ERRATA_REFRESH_URL,
                access_token=settings.ERRATA_SERVER_TOKEN,
                user=self.user.name,
                ip=self.user.ip,
            )
            results = service.collect().results
        except Exception as e:
            self.store_error(
                message={"message": f"Errata Server error: {e}"},
                severity=self.LL.ERROR,
                http_code=getattr(e, "status_code") or 500,
            )
            return []

        self.status = True

        for err in results:
            reverted_errata = revert_patch(err.errata, err.patch)

            # XXX: ignore non-CVE, because other vulns are only linked to CVE
            discarded_cves = [
                ref
                for ref in err.patch.del_vulns
                if ref.type == "vuln" and ref.link.startswith(CVE_ID_PREFIX)
            ]

            if discarded_cves:
                yield (reverted_errata, err.patch)

    def get_suspicious_changes_from_transaction_id(self) -> Iterable[ErrataWithPatch]:
        self.status = False

        response = self.send_sql_request(
            self.sql.get_errata_history_by_transaction_id.format(
                transaction_id=UUID(self.args["transaction_id"]),
            )
        )
        if not self.sql_status:
            return []

        self.status = True

        for ec_type, _, old, new in response:
            old_eh = ErrataHistory(
                *old[:6],
                [Reference(*p) for p in old[6]],  # type: ignore
                *old[7:],
            )
            new_eh = ErrataHistory(
                *new[:6],
                [Reference(*p) for p in new[6]],  # type: ignore
                *new[7:],
            )
            if ec_type == "update":
                patch = ReferencesPatch.from_history(
                    old_eh.references, new_eh.references
                )
            elif ec_type == "discard":
                patch = ReferencesPatch.from_history(new_eh.references, [])
            else:
                raise ValueError(f"Unknown errata change type: {ec_type}")

            # XXX: ignore non-CVE, because other vulns are only linked to CVE
            discarded_cves = [
                ref
                for ref in patch.del_vulns
                if ref.type == "vuln" and ref.link.startswith(CVE_ID_PREFIX)
            ]

            if discarded_cves:
                yield (new_eh, patch)

    def get_suspicious_changes(self) -> list[ErrataWithPatch]:
        if self.args["transaction_id"] is not None:
            method = self.get_suspicious_changes_from_transaction_id
        else:
            method = self.get_suspicious_changes_from_errata_server

        return list(method())

    def get_rejected_cves_ids(self, cves_ids: Iterable[str]) -> set[str]:
        self.status = False
        _tmp_table_name = make_tmp_table_name("cves_ids")
        response = self.send_sql_request(
            self.sql.get_rejected_cves_ids.format(tmp_table_name=_tmp_table_name),
            external_tables=[
                {
                    "name": _tmp_table_name,
                    "structure": [("vuln_id", "String")],
                    "data": [{"vuln_id": cve_id} for cve_id in cves_ids],
                },
            ],
        )
        if not self.sql_status:
            return set()

        self.status = True

        # TODO: Check rejection of other (not CVE) vulnerabilities.
        # The main reason why it can't be done for now is that we almost don't have
        # GHSA in Errata references and BDU don't provide information about rejection.
        return {row[0] for row in response}

    def get_cve_cpe_triplets_histories(
        self, cves_ids: Iterable[str]
    ) -> dict[str, list[set[CpeTriplet]]]:
        self.status = False
        _tmp_table_name = make_tmp_table_name("cves_ids")
        response = self.send_sql_request(
            self.sql.get_cve_cpe_history.format(tmp_table_name=_tmp_table_name),
            external_tables=[
                {
                    "name": _tmp_table_name,
                    "structure": [("vuln_id", "String")],
                    "data": [{"vuln_id": cve_id} for cve_id in cves_ids],
                },
            ],
        )
        if not self.sql_status:
            return {}

        cve_cpe_triplets_history = defaultdict(list)
        for cve_id, changes_history in response:
            for _, cpe_matches in changes_history:
                cpe_triplets_at_history_point = set()
                for cpe_match in cpe_matches:
                    try:
                        cpe_triplet = parse_cpe(cpe_match)
                        cpe_triplets_at_history_point.add(cpe_triplet)
                    except ValueError:
                        self.logger.warning(f"Failed to parse CPE: {cpe_match}")
                cve_cpe_triplets_history[cve_id].append(cpe_triplets_at_history_point)

        self.status = True
        return cve_cpe_triplets_history

    def get_cpe_triplets_packages(
        self, pkgs_names: Iterable[str]
    ) -> dict[CpeTriplet, set[str]]:
        self.status = False
        _tmp_table_name = make_tmp_table_name("pkgs_names")
        response = self.send_sql_request(
            self.sql.get_cpe_triplets_packages.format(
                pnc_branches=("altsisyphus", "alt_p11", "alt_p10", "alt_p9"),
                tmp_table_name=_tmp_table_name,
            ),
            external_tables=[
                {
                    "name": _tmp_table_name,
                    "structure": [("pkg_name", "String")],
                    "data": [{"pkg_name": pkg_name} for pkg_name in pkgs_names],
                },
            ],
        )
        if not self.sql_status:
            return {}

        packages_cpe_triplets = defaultdict(set)
        for cpe_triplet_str, matched_names in response:
            try:
                cpe_triplet = parse_cpe(cpe_triplet_str)
                packages_cpe_triplets[cpe_triplet].update(matched_names)
            except ValueError:
                self.logger.warning(f"Failed to parse CPE: {cpe_triplet_str}")

        self.status = True
        return packages_cpe_triplets

    def get(self) -> WorkerResult:
        suspicious_changes = self.get_suspicious_changes()
        if not self.status:
            return self.error

        if not suspicious_changes:
            return "No vulnerabilities discards", 404

        # 0. collect mapping of CVE:ErrataID
        cve_errata_mapping: dict[str, set[str]] = defaultdict(set)
        for errata, patch in suspicious_changes:
            for ref in patch.del_vulns:
                if ref.type == "vuln" and ref.link.startswith(CVE_ID_PREFIX):
                    cve_errata_mapping[ref.link].add(errata.id)

        # 1. collect rejected CVE's
        rejected_cves_ids = self.get_rejected_cves_ids(cve_errata_mapping)
        if not self.status:
            return self.error

        # 2. collect non-rejected CVE:[CpeTriplet] matches histories
        non_rejected_cves_ids = set(cve_errata_mapping).difference(rejected_cves_ids)
        cve_cpe_histories = self.get_cve_cpe_triplets_histories(non_rejected_cves_ids)
        if not self.status:
            return self.error

        # 2.1. collect active CpeTriplet:[Package] matches from PackagesNameConversion
        cpe_triplets_packages = self.get_cpe_triplets_packages(
            pkgs_names={errata.pkg_name for errata, _ in suspicious_changes}
        )
        if not self.status:
            return self.error

        # 2.2. and reversed mapping (Package:[CpeTriplet]) to reduce algorithm complexity
        packages_cpe_triplets: dict[str, set[CpeTriplet]] = defaultdict(set)
        for cpe_triplet, pkg_names in cpe_triplets_packages.items():
            for pkg_name in pkg_names:
                packages_cpe_triplets[pkg_name].add(cpe_triplet)

        def classify(vuln_id: str, pkg_name: str) -> str:
            # Only for CVE for now
            if not vuln_id.startswith(CVE_ID_PREFIX):
                return "Skipped analysis (not a CVE)"

            # Check if CVE is rejected
            if vuln_id in rejected_cves_ids:
                return "Rejected by upstream"

            # Check we have CpeTriplet matches
            if not (package_cpe_triplets := packages_cpe_triplets.get(pkg_name)):
                return "No active PNC matches found"

            # Check CpeTriplet matches
            if not (cpe_history := cve_cpe_histories.get(vuln_id)):
                return "No CPE matches in the database"

            # Check if current (last) history moment of CVE has CpeTriplet matches
            if cpe_history[-1].intersection(package_cpe_triplets):
                return "Changed version(s) in CPE match(es)"

            # Check if matches are lost by finding the most recent historical match
            for cpe_triplets_at_moment in reversed(cpe_history):
                last_matches = cpe_triplets_at_moment.intersection(package_cpe_triplets)
                if last_matches:
                    return "Upstream removed/changed CPE triplets: {}".format(
                        ", ".join(
                            f"'{cpe_triplet_to_str(match)}'" for match in last_matches
                        )
                    )

            return "Erroneous match"

        return {
            "changes": [
                {
                    "errata": errata._asdict()
                    | {"references": [ref._asdict() for ref in errata.references]},
                    "discards": sorted(
                        (
                            {
                                "vuln_id": r.link,
                                "reason": classify(r.link, errata.pkg_name),
                            }
                            for r in patch.del_vulns
                        ),
                        key=lambda x: (x["vuln_id"]),
                    ),
                }
                for errata, patch in suspicious_changes
            ],
        }, 200
