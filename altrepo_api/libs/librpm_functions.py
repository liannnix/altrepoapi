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

import ctypes

from enum import IntEnum
from typing import NamedTuple, Union

LIBRPM_SO = "librpm.so.7"
RPMSENSE_MASK = 0x0F
RPMSENSE_EQUAL = 0x08

# import librpm library
librpm = ctypes.CDLL(LIBRPM_SO)
LIBRPM_NOPROMOTE = ctypes.c_int.in_dll(librpm, "_rpmds_nopromote")

# rpmRangesOverlap function interface
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


# rpmEVRDTCompare function interface
class struct_rpmEVRDT(ctypes.Structure):
    _fields_ = [
        ("has_epoch", ctypes.c_int),
        ("epoch", ctypes.c_ulonglong),
        ("version", ctypes.c_char_p),
        ("release", ctypes.c_char_p),
        ("disttag", ctypes.c_char_p),
        ("has_buildtime", ctypes.c_int),
        ("buildtime", ctypes.c_ulonglong),
    ]


rpmEVRDTCompare = librpm.rpmEVRDTCompare
rpmEVRDTCompare.argtypes = [
    ctypes.POINTER(struct_rpmEVRDT),  # fst
    ctypes.POINTER(struct_rpmEVRDT),  # snd
]
rpmEVRDTCompare.restype = ctypes.c_int


class Dependency(NamedTuple):
    name: str
    version: str
    flags: int


class struct_Dependency(NamedTuple):
    name: bytes
    version: bytes
    flags: int


class VersionCompareResult(IntEnum):
    LESS_THAN = -1
    EQUAL = 0
    GREATER_THAN = 1


def _make_dependency_tuple(name: str, version: str, flags: int) -> struct_Dependency:
    return struct_Dependency(
        name=name.encode("utf-8"),
        version=version.encode("utf-8"),
        flags=(RPMSENSE_MASK & flags),
    )


def _check_dependency_overlap(
    provide_dep: struct_Dependency, require_dep: struct_Dependency
) -> bool:
    # set flags for `provides` dependency to RPMSENSE_EQUAL as apt-rpm does
    _provide_dep = struct_Dependency(*provide_dep)._replace(flags=RPMSENSE_EQUAL)
    return bool(rpmRangesOverlap(*_provide_dep, *require_dep, LIBRPM_NOPROMOTE))


def check_dependency_overlap(
    provide_dep_name: str,
    provide_dep_version: str,
    provide_dep_flags: int,
    require_dep_name: str,
    require_dep_version: str,
    require_dep_flags: int,
) -> bool:
    """Check dependencies overlapping using librpm `rpmRangesOverlap` function."""
    return _check_dependency_overlap(
        _make_dependency_tuple(
            provide_dep_name, provide_dep_version, provide_dep_flags
        ),
        _make_dependency_tuple(
            require_dep_name, require_dep_version, require_dep_flags
        ),
    )


def _make_rpm_evrdt_struct(
    epoch: Union[int, None],
    version: str,
    release: str,
    disttag: str,
    buildtime: Union[int, None],
) -> struct_rpmEVRDT:
    return struct_rpmEVRDT(
        1 if epoch is not None else 0,  # has_epoch
        epoch if epoch is not None else 0,
        version.encode("utf-8"),
        release.encode("utf-8"),
        disttag.encode("utf-8"),
        1 if buildtime is not None else 0,  # has_buildtime
        buildtime if buildtime is not None else 0,
    )


def _compare_versions(version1: struct_rpmEVRDT, version2: struct_rpmEVRDT) -> int:
    return rpmEVRDTCompare(ctypes.byref(version1), ctypes.byref(version2))


def compare_versions(
    *,
    epoch1: Union[int, None] = None,
    version1: str = "",
    release1: str = "",
    disttag1: str = "",
    buildtime1: Union[int, None] = None,
    epoch2: Union[int, None] = None,
    version2: str = "",
    release2: str = "",
    disttag2: str = "",
    buildtime2: Union[int, None] = None
) -> VersionCompareResult:
    """Compare package versions using librpm `rpmEVRDTCompare` function."""
    return VersionCompareResult(
        _compare_versions(
            _make_rpm_evrdt_struct(epoch1, version1, release1, disttag1, buildtime1),
            _make_rpm_evrdt_struct(epoch2, version2, release2, disttag2, buildtime2),
        )
    )


def version_less_or_equal(
    version1: str, version2: str, strictly_less: bool = False
) -> bool:
    """Simple version comparison without additional field (epoch, release, disttag,...)."""
    eq = compare_versions(version1=version1, version2=version2)
    if strictly_less:
        return eq < VersionCompareResult.EQUAL
    else:
        return eq < VersionCompareResult.GREATER_THAN
