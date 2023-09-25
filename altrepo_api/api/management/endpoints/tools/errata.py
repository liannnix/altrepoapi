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

from typing import Any, Union

from altrepo_api.utils import mmhash

from .base import Errata, ErrataID, ErrataManageError, Reference
from .constants import ERRATA_REFERENCE_TYPE, DT_NEVER
from .errata_id import ErrataIDService, update_errata_id
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
    )
    return errata._replace(hash=errata_hash(errata))


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


def build_errata_with_id_version_updated(
    eid_service: ErrataIDService, errata: Errata
) -> Errata:
    """Registers new errata id version and returns updated errata object."""

    new_eid = update_errata_id(eid_service, errata.id.id)  # type: ignore
    return errata.update(id=new_eid.id, updated=new_eid.updated)


def _do_bulletin_update(
    eid_service: ErrataIDService,
    bulletin: Errata,
    errata: Errata,
    new_errata: Union[Errata, None],
) -> Union[Errata, None]:
    b_refs = bulletin.references[:]
    old_errata_id = errata.id.id  # type: ignore
    new_errata_id = new_errata.id.id if new_errata is not None else None  # type: ignore

    # delete old errata id from bulletin references
    for i, br in enumerate(bulletin.references):
        if br.link == old_errata_id:
            b_refs.pop(i)
            break

    # add new errata id to bulletin refernces if provided
    if new_errata_id is not None:
        b_refs.append(Reference(ERRATA_REFERENCE_TYPE, new_errata_id))

    # update bulletin errata id version if updated references is not empty
    if b_refs != []:
        new_bulletin = build_errata_with_id_version_updated(
            eid_service, bulletin
        ).update(
            # XXX: sort errata references to be consistent with DB contents!
            references=sorted(b_refs)
        )
        # calculate hash from updated errata references
        new_bulletin = new_bulletin.update(hash=errata_hash(new_bulletin))
        return new_bulletin

    return None


def build_new_bulletin_by_errata_update(
    *,
    eid_service: ErrataIDService,
    bulletin: Errata,
    errata: Errata,
    new_errata: Errata,
) -> Errata:
    """Registers new errata id version for bulletin and returns updated bulletin object
    using data from old and new errata ids."""

    new_bulletin = _do_bulletin_update(eid_service, bulletin, errata, new_errata)

    if new_bulletin is None:
        raise ErrataManageError(
            f"Failed to update bulletin {bulletin.id} with {new_errata.id}"
        )

    return new_bulletin


def build_new_bulletin_by_errata_discard(
    *,
    eid_service: ErrataIDService,
    bulletin: Errata,
    errata: Errata,
) -> Union[Errata, None]:
    """Registers new errata id version for bulletin if references is not empty after
    removing discarded errata id from it."""

    return _do_bulletin_update(eid_service, bulletin, errata, None)
