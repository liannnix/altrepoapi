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

from typing import Any, Union

from altrepo_api.utils import mmhash

from .base import Branch, Errata, ErrataID, Reference
from .constants import (
    BRANCH_BULLETIN_ERRATA_SOURCE,
    BRANCH_BULLETIN_ERRATA_TYPE,
    ERRATA_REFERENCE_TYPE,
    DT_NEVER,
)
from .errata_id import (
    ErrataIDServiceProtocol,
    update_errata_id,
    register_branch_update_id,
)
from .utils import dt_from_iso, re_errata_id


def errata_hash(errata: Errata) -> int:
    """Calculates errata object hash to be consistent with DB contents."""

    # XXX: sort errata references before hashing to be consistent with DB contents
    return mmhash("".join([f"{el[0]}:{el[1]}" for el in sorted(errata.references)]))


def json2errata(data: dict[str, Any]) -> Errata:
    """Converts JSON representation to Errata object instance."""

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
        # XXX: optional value, default is False
        is_discarded=data.get("is_discarded", False),
    )
    return errata.update(hash=errata_hash(errata))


def build_stub_errata(errata_id: str) -> Errata:
    return Errata(
        id=(ErrataID.from_id(errata_id)),
        type="",
        source="",
        created=DT_NEVER,
        updated=DT_NEVER,
        pkg_hash=0,
        pkg_name="",
        pkg_version="",
        pkg_release="",
        pkgset_name="",
        task_id=0,
        subtask_id=0,
        task_state="",
        references=[],
        hash=0,
    )


def build_new_bulletin(
    eid_service: ErrataIDServiceProtocol, errata: Errata, branch_state: Branch
) -> Errata:
    """Builds new bulletin errata record object from errata
    and registers new errata ID for it."""

    eid = register_branch_update_id(eid_service, branch_state.date.year)
    bulletin = Errata(
        id=(ErrataID.from_id(eid.id)),
        type=BRANCH_BULLETIN_ERRATA_TYPE,
        source=BRANCH_BULLETIN_ERRATA_SOURCE,
        created=branch_state.date,
        updated=eid.updated,
        pkg_hash=0,
        pkg_name="",
        pkg_version="",
        pkg_release="",
        pkgset_name=branch_state.name,
        task_id=0,
        subtask_id=0,
        task_state="",
        references=[Reference(type=ERRATA_REFERENCE_TYPE, link=errata.id.id)],  # type: ignore
        hash=0,
    )
    return bulletin.update(hash=errata_hash(bulletin))


def build_errata_with_id_version_updated(
    eid_service: ErrataIDServiceProtocol, errata: Errata
) -> Errata:
    """Registers new errata id version and returns updated errata object."""

    new_eid = update_errata_id(eid_service, errata.id.id)  # type: ignore
    return errata.update(id=new_eid.id, updated=new_eid.updated)


def _do_bulletin_update(
    eid_service: ErrataIDServiceProtocol,
    bulletin: Errata,
    errata: Union[Errata, None],
    new_errata: Union[Errata, None],
) -> Errata:
    b_refs = bulletin.references[:]
    old_errata_id = errata.id.id if errata is not None else None  # type: ignore
    new_errata_id = new_errata.id.id if new_errata is not None else None  # type: ignore

    # delete old errata id from bulletin references if provided
    if old_errata_id is not None:
        for i, br in enumerate(bulletin.references):
            if br.link == old_errata_id:
                b_refs.pop(i)
                break

    # add new errata id to bulletin refernces if provided
    if new_errata_id is not None:
        b_refs.append(Reference(ERRATA_REFERENCE_TYPE, new_errata_id))

    # update bulletin errata id version if updated references is not empty
    new_bulletin = build_errata_with_id_version_updated(eid_service, bulletin).update(
        # XXX: sort errata references to be consistent with DB contents!
        references=sorted(b_refs)
    )
    # set 'is_discarded' flag if refs are empty
    if not b_refs:
        new_bulletin = new_bulletin.update(is_discarded=True)
    # calculate hash from updated errata references
    new_bulletin = new_bulletin.update(hash=errata_hash(new_bulletin))

    return new_bulletin


def update_bulletin_by_errata_update(
    *,
    eid_service: ErrataIDServiceProtocol,
    bulletin: Errata,
    errata: Errata,
    new_errata: Errata,
) -> Errata:
    """Registers new errata id version for bulletin and returns updated bulletin object
    using data from old and new errata ids."""

    return _do_bulletin_update(eid_service, bulletin, errata, new_errata)


def update_bulletin_by_errata_discard(
    *,
    eid_service: ErrataIDServiceProtocol,
    bulletin: Errata,
    errata: Errata,
) -> Errata:
    """Registers new errata id version for bulletin if references is not empty after
    removing discarded errata id from it."""

    return _do_bulletin_update(eid_service, bulletin, errata, None)


def update_bulletin_by_errata_add(
    *,
    eid_service: ErrataIDServiceProtocol,
    bulletin: Errata,
    new_errata: Errata,
) -> Errata:
    """Registers new errata id version for bulletin and returns updated bulletin object
    using data from new errata id."""

    return _do_bulletin_update(eid_service, bulletin, None, new_errata)
