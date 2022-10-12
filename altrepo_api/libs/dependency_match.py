# ALTRepo API
# Copyright (C) 2021-2022  BaseALT Ltd

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

import ctypes

from typing import NamedTuple

LIBRPM_SO = "librpm.so.7"
RPMSENSE_MASK = 0x0F
RPMSENSE_EQUAL = 0x08

# import librpm library
librpm = ctypes.CDLL(LIBRPM_SO)

rpmRangesOverlap = librpm.rpmRangesOverlap
rpmRangesOverlap.argtypes = [
    ctypes.c_char_p,
    ctypes.c_char_p,
    ctypes.c_uint32,
    ctypes.c_char_p,
    ctypes.c_char_p,
    ctypes.c_uint32,
    ctypes.c_int,
]
rpmRangesOverlap.restype = ctypes.c_int

LIBRPM_NOPROMOTE = ctypes.c_int.in_dll(librpm, "_rpmds_nopromote")


class Dependency(NamedTuple):
    name: bytes
    version: bytes
    flags: int


def make_dependency_tuple(name: str, version: str, flags: int) -> Dependency:
    return Dependency(
        name=name.encode("utf-8"),
        version=version.encode("utf-8"),
        flags=(RPMSENSE_MASK & flags),
    )


def check_dependency_overlap(provide_dep: Dependency, require_dep: Dependency) -> bool:
    """Check dependencies overlapping using librpm `rpmRangesOverlap` function."""
    # set flags for `provides` dependency to RPMSENSE_EQUAL as apt-rpm does
    _provide_dep = Dependency(*provide_dep)._replace(flags=RPMSENSE_EQUAL)
    return bool(rpmRangesOverlap(*_provide_dep, *require_dep, LIBRPM_NOPROMOTE))
