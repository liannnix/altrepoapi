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

from typing import Any

from altrepo_api.utils import mmhash

from .base import Errata, ErrataID, Reference
from .constants import ERRATA_REFERENCE_TYPE
from .errata_id import ErrataIDService, update_errata_id
from .utils import dt_from_iso, re_errata_id


def errata_hash(errata: Errata) -> int:
    # XXX: sort errata references before hashing to be consistent with DB contents
    return mmhash("".join([f"{el[0]}:{el[1]}" for el in sorted(errata.references)]))


def json2errata(data: dict[str, Any]) -> Errata:
    errata = Errata(
        id=(
            ErrataID.from_id(data["id"]) if re_errata_id.fullmatch(data["id"]) else None
        ),
        type=data["type"],
        source=data["source"],
        created=dt_from_iso(data["created"]),
        updated=dt_from_iso(data["updated"]),
        pkg_hash=int(data["pkg_hash"]),
        pkg_name=data["pkg_name"],
        pkg_version=data["pkg_version"],
        pkg_release=data["pkg_release"],
        pkgset_name=data["pkgset_name"],
        task_id=int(data["task_id"]),
        subtask_id=int(data["subtask_id"]),
        task_state=data["task_state"],
        # XXX: sort errata references to be consistent with DB contents!
        references=sorted(Reference(**v) for v in data["references"]),
        hash=0,
    )
    return errata._replace(hash=errata_hash(errata))


def build_errata_with_updated_id(eid_service: ErrataIDService, errata: Errata) -> Errata:
    return errata.update(update_errata_id(eid_service, errata.id.id)._asdict())  # type: ignore


def build_new_bulletin_errata(
    eid_service: ErrataIDService, bulletin: Errata, errata: Errata, new_errata: Errata
) -> Errata:
    b_refs = bulletin.references[:]
    old_errata_id = errata.id.id  # type: ignore
    new_errata_id = new_errata.id.id  # type: ignore

    for i, br in enumerate(bulletin.references):
        if br.link == old_errata_id:
            b_refs.pop(i)
            break

    b_refs.append(Reference(ERRATA_REFERENCE_TYPE, new_errata_id))

    new_bulletin = build_errata_with_updated_id(eid_service, bulletin).update_kw(
        # XXX: sort errata references to be consistent with DB contents!
        references=sorted(b_refs)
    )
    new_bulletin = new_bulletin.update_kw(hash=errata_hash(new_bulletin))

    return new_bulletin
