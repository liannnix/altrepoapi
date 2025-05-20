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

from typing import Iterable

from altrepodb_libs import PackageCveMatch

from altrepo_api.utils import make_tmp_table_name
from altrepo_api.api.misc import lut

from .base import _pAPIWorker
from ..base import PncRecord


def get_pncs_by_package(
    cls: _pAPIWorker, package_name: str, states: tuple[str, ...]
) -> list[PncRecord]:
    """Collects active PNC records by given package name and tuple of states.."""

    cls.status = False
    pncs_by_package = []

    # collect PNC records by package name
    where_clause = f"WHERE state IN {states} AND name = '{package_name}'"

    response = cls.send_sql_request(
        cls.sql.get_pnc_records.format(
            where_clause=where_clause, pnc_branches=tuple(lut.repology_branches)
        )
    )
    if not cls.sql_status:
        return []

    pncs_by_package = [PncRecord(*el) for el in response]

    cls.status = True
    return pncs_by_package


def get_cpes_by_projects(
    cls: _pAPIWorker, projects: Iterable[str], states: tuple[str, ...]
) -> dict[str, list[PncRecord]]:
    """Collects CPE records by given project' names and tuple of states."""

    cls.status = False

    cpes: dict[str, list[PncRecord]] = {}
    tmp_table = make_tmp_table_name("project_names")
    response = cls.send_sql_request(
        cls.sql.get_cpes_by_project_names.format(
            tmp_table=tmp_table, cpe_states=states
        ),
        external_tables=[
            {
                "name": tmp_table,
                "structure": [
                    ("project_name", "String"),
                ],
                "data": [{"project_name": p} for p in projects],
            },
        ],
    )
    if not cls.sql_status:
        return {}
    if response:
        for p in (PncRecord(*el) for el in response):
            cpes.setdefault(p.pkg_name, []).append(p)

    cls.status = True
    return cpes


def get_pkgs_cve_matches_by_hashes(
    cls: _pAPIWorker, match_hashes: Iterable[int]
) -> list[PackageCveMatch]:
    cls.status = False

    tmp_table = make_tmp_table_name("pkgs_match_hashes")

    response = cls.send_sql_request(
        cls.sql.get_pkg_cve_matches_by_hashes.format(tmp_table=tmp_table),
        external_tables=[
            {
                "name": tmp_table,
                "structure": [("key_hash", "UInt64")],
                "data": [{"key_hash": h} for h in match_hashes],
            },
        ],
    )
    if not cls.sql_status or not response:
        return []

    cls.status = True
    return [PackageCveMatch(*el) for el in response]
