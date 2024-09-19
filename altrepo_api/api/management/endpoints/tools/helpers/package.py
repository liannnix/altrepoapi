# ALTRepo API
# Copyright (C) 2021-2024  BaseALT Ltd

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

from typing import Iterable, NamedTuple

from altrepo_api.api.misc import lut
from altrepo_api.utils import make_tmp_table_name

from .base import _pAPIWorker
from ..base import PncRecord, PncChangeRecord


def get_related_packages_by_project_name(
    cls: _pAPIWorker, project_names: list[str]
) -> list[str]:
    """Get related packages by project name from 'PackagesNameConversion' table."""

    cls.status = False
    res = []

    tmp_table = make_tmp_table_name("project_names")

    response = cls.send_sql_request(
        cls.sql.get_packages_by_project_names.format(
            tmp_table=tmp_table,
            cpe_branches=lut.repology_branches,
        ),
        external_tables=[
            {
                "name": tmp_table,
                "structure": [("pkg_name", "String")],
                "data": [{"pkg_name": n} for n in project_names],
            },
        ],
    )
    if not cls.sql_status:
        return []
    if response:
        res = [el[0] for el in response]

    cls.status = True
    return res


def store_pnc_records(cls: _pAPIWorker, pnc_records: list[PncRecord]) -> None:
    cls.status = False

    _ = cls.send_sql_request(
        (cls.sql.store_pnc_records, [pnc.asdict() for pnc in pnc_records])
    )
    if not cls.sql_status:
        return None

    cls.status = True


def store_pnc_change_records(
    cls: _pAPIWorker, pnc_change_records: list[PncChangeRecord]
) -> None:
    def pnc_change_records_gen():
        for pncc in pnc_change_records:
            res = {
                "transaction_id": str(pncc.id),
                "pncc_user": pncc.reason.actor.name,
                "pncc_user_ip": pncc.reason.actor.ip,
                "pncc_reason": pncc.reason.serialize(),
                "pncc_type": pncc.type.value,
                "pncc_source": pncc.source.value,
                "pncc_origin": pncc.origin.value,
            }
            res.update(**pncc.pnc.asdict())
            yield res

    cls.status = False

    _ = cls.send_sql_request(
        (cls.sql.store_pnc_change_records, pnc_change_records_gen())
    )
    if not cls.sql_status:
        return None

    cls.status = True


def get_pkgs_branch_and_evr_by_hashes(
    cls: _pAPIWorker, hashes: Iterable[int]
) -> dict[str, dict[str, str]]:
    class PkgInfo(NamedTuple):
        pkg_hash: str
        pkg_name: str
        pkg_version: str
        pkg_release: str
        branch: str

    cls.status = False
    res = {}

    tmp_table = make_tmp_table_name("pkg_hashes")

    response = cls.send_sql_request(
        cls.sql.get_packages_info_by_hashes.format(tmp_table=tmp_table),
        external_tables=[
            {
                "name": tmp_table,
                "structure": [("pkg_hash", "UInt64")],
                "data": [{"pkg_hash": n} for n in hashes],
            },
        ],
    )
    if not cls.sql_status:
        return {}
    for p in (PkgInfo(*el) for el in response):
        if p.pkg_hash not in res:
            res[p.pkg_hash] = p._asdict()
            res[p.pkg_hash]["branch"] = [res[p.pkg_hash]["branch"]]
        else:
            res[p.pkg_hash]["branch"].append(p.branch)

    cls.status = True
    return res
