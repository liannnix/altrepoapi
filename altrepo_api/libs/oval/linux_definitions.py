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

import xml.etree.ElementTree as xml

from dataclasses import dataclass
from typing import Optional

from .oval_definitions.enumeration import (
    ExistenceEnumeration,
    OperatorEnumeration,
    CheckEnumeration,
)
from .oval_definitions.type import (
    ObjectRefType,
    StateRefType,
    ObjectType,
    NotesType,
    StateType,
    TestType,
    Signature,
    Filter,
)
from .oval_definitions.entity import (
    # object entities
    EntityObjectIntType,
    EntityObjectStringType,
    EntityObjectAnySimpleType,
    # state entities
    EntityStateBoolType,
    EntityStateStringType,
    EntityStateAnySimpleType,
    EntityStateEVRStringType,
    EntityStateRpmVerifyResultType,
)
from .oval_definitions.utils import bool_to_xml


# PartInfo classes
@dataclass
class PartitionObject(ObjectType):
    mount_point: EntityObjectStringType = None  # type: ignore
    filters: Optional[list[Filter]] = None

    def __init__(
        self,
        *,
        id: str,
        version: int,
        mount_point: EntityObjectStringType,
        filters: Optional[list[Filter]] = None,
        comment: Optional[str] = None,
        deprecated: Optional[bool] = None,
        notes: Optional[NotesType] = None,
        signature: Optional[Signature] = None,
    ):
        self.mount_point = mount_point
        self.filters = filters
        super().__init__(
            "partition_object", id, version, comment, deprecated, notes, signature
        )

    def to_xml(self) -> xml.Element:
        r = super().to_xml()
        r.append(self.mount_point.to_xml())

        if self.filters:
            for fl in self.filters:
                r.append(fl.to_xml())

        return r


@dataclass
class PartitionState(StateType):
    mount_point: Optional[EntityObjectStringType] = None
    device: Optional[EntityObjectStringType] = None
    uuid: Optional[EntityObjectStringType] = None
    fs_type: Optional[EntityObjectStringType] = None
    mount_options: Optional[EntityObjectStringType] = None
    total_space: Optional[EntityObjectIntType] = None
    space_used: Optional[EntityObjectIntType] = None
    space_left: Optional[EntityObjectIntType] = None

    def __init__(
        self,
        *,
        id: str,
        version: int,
        mount_point: Optional[EntityObjectStringType] = None,
        device: Optional[EntityObjectStringType] = None,
        uuid: Optional[EntityObjectStringType] = None,
        fs_type: Optional[EntityObjectStringType] = None,
        mount_options: Optional[EntityObjectStringType] = None,
        total_space: Optional[EntityObjectIntType] = None,
        space_used: Optional[EntityObjectIntType] = None,
        space_left: Optional[EntityObjectIntType] = None,
        comment: Optional[str] = None,
        operator: Optional[OperatorEnumeration] = None,
        deprecated: Optional[bool] = None,
        notes: Optional[NotesType] = None,
        signature: Optional[Signature] = None,
    ):
        self.mount_point = mount_point
        self.device = device
        self.uuid = uuid
        self.fs_type = fs_type
        self.mount_options = mount_options
        self.total_space = total_space
        self.space_used = space_used
        self.space_left = space_left
        super().__init__(
            "partition_state",
            id,
            version,
            comment,
            operator,
            deprecated,
            notes,
            signature,
        )

    def to_xml(self) -> xml.Element:
        r = super().to_xml()

        if self.mount_point is not None:
            r.append(self.mount_point.to_xml())
        if self.device is not None:
            r.append(self.device.to_xml())
        if self.uuid is not None:
            r.append(self.uuid.to_xml())
        if self.fs_type is not None:
            r.append(self.fs_type.to_xml())
        if self.mount_options is not None:
            r.append(self.mount_options.to_xml())
        if self.total_space is not None:
            r.append(self.total_space.to_xml())
        if self.space_used is not None:
            r.append(self.space_used.to_xml())
        if self.space_left is not None:
            r.append(self.space_left.to_xml())

        return r


@dataclass
class PartitionTest(TestType):
    def __init__(
        self,
        *,
        id: str,
        version: int,
        check: CheckEnumeration,
        comment: str,
        object: ObjectRefType,
        states: Optional[list[StateRefType]] = None,
        check_existence: Optional[ExistenceEnumeration] = None,
        state_operator: Optional[OperatorEnumeration] = None,
        deprecated: Optional[bool] = None,
        notes: Optional[NotesType] = None,
        signature: Optional[Signature] = None,
    ):
        super().__init__(
            "partition_test",
            id,
            version,
            check,
            comment,
            object,
            states,
            check_existence,
            state_operator,
            deprecated,
            notes,
            signature,
        )


# RPMInfo classes
@dataclass
class RpmInfoBehaviors:
    filepaths: Optional[bool] = None
    _tag = "behaviors"

    def to_xml(self) -> xml.Element:
        r = xml.Element(self._tag)
        if self.filepaths is not None:
            r.set("filepaths", bool_to_xml(self.filepaths))
        return r


@dataclass
class RPMInfoObject(ObjectType):
    name: EntityObjectStringType = None  # type: ignore
    behaviors: Optional[RpmInfoBehaviors] = None
    filters: Optional[list[Filter]] = None

    def __init__(
        self,
        *,
        id: str,
        version: int,
        name: EntityObjectStringType,
        behaviors: Optional[RpmInfoBehaviors] = None,
        filters: Optional[list[Filter]] = None,
        comment: Optional[str] = None,
        deprecated: Optional[bool] = None,
        notes: Optional[NotesType] = None,
        signature: Optional[Signature] = None,
    ):
        self.name = name
        self.behaviors = behaviors
        self.filters = filters
        super().__init__(
            "rpminfo_object", id, version, comment, deprecated, notes, signature
        )

    def to_xml(self) -> xml.Element:
        r = super().to_xml()
        r.append(self.name.to_xml())

        if self.behaviors is not None:
            r.append(self.behaviors.to_xml())

        if self.filters:
            for fl in self.filters:
                r.append(fl.to_xml())

        return r


@dataclass
class RPMInfoState(StateType):
    name: Optional[EntityStateStringType] = None
    arch: Optional[EntityStateStringType] = None
    epoch: Optional[EntityStateAnySimpleType] = None
    release: Optional[EntityStateAnySimpleType] = None
    pkg_version: Optional[EntityStateAnySimpleType] = None
    evr: Optional[EntityStateEVRStringType] = None
    signature_keyid: Optional[EntityStateStringType] = None
    # NAME-EPOCH:VERSION-RELEASE.ARCHITECTURE / NAME-0:VERSION-RELEASE.ARCHITECTURE
    extended_name: Optional[EntityStateStringType] = None
    filepath: Optional[EntityStateStringType] = None

    def __init__(
        self,
        *,
        id: str,
        version: int,
        name: Optional[EntityStateStringType] = None,
        arch: Optional[EntityStateStringType] = None,
        epoch: Optional[EntityStateAnySimpleType] = None,
        release: Optional[EntityStateAnySimpleType] = None,
        pkg_version: Optional[EntityStateAnySimpleType] = None,
        evr: Optional[EntityStateEVRStringType] = None,
        signature_keyid: Optional[EntityStateStringType] = None,
        extended_name: Optional[EntityStateStringType] = None,
        filepath: Optional[EntityStateStringType] = None,
        comment: Optional[str] = None,
        operator: Optional[OperatorEnumeration] = None,
        deprecated: Optional[bool] = None,
        notes: Optional[NotesType] = None,
        signature: Optional[Signature] = None,
    ):
        self.name = name
        self.arch = arch
        self.epoch = epoch
        self.release = release
        self.pkg_version = pkg_version
        self.evr = evr
        self.signature_keyid = signature_keyid
        self.extended_name = extended_name
        self.filepath = filepath
        super().__init__(
            "rpminfo_state",
            id,
            version,
            comment,
            operator,
            deprecated,
            notes,
            signature,
        )

    def to_xml(self) -> xml.Element:
        r = super().to_xml()

        if self.name is not None:
            r.append(self.name.to_xml())
        if self.arch is not None:
            r.append(self.arch.to_xml())
        if self.epoch is not None:
            # special case for  epoch value `0` to comply with `rpm -q --qf '%{EPOCH}\n'` result
            if self.epoch.value == "0":
                self.epoch.value = "(none)"
            r.append(self.epoch.to_xml())
        if self.release is not None:
            r.append(self.release.to_xml())
        if self.pkg_version is not None:
            r.append(self.pkg_version.to_xml())
        if self.evr is not None:
            r.append(self.evr.to_xml())
        if self.signature_keyid is not None:
            r.append(self.signature_keyid.to_xml())
        if self.filepath is not None:
            r.append(self.filepath.to_xml())

        return r


@dataclass
class RPMInfoTest(TestType):
    def __init__(
        self,
        *,
        id: str,
        version: int,
        check: CheckEnumeration,
        comment: str,
        object: ObjectRefType,
        states: Optional[list[StateRefType]] = None,
        check_existence: Optional[ExistenceEnumeration] = None,
        state_operator: Optional[OperatorEnumeration] = None,
        deprecated: Optional[bool] = None,
        notes: Optional[NotesType] = None,
        signature: Optional[Signature] = None,
    ):
        super().__init__(
            "rpminfo_test",
            id,
            version,
            check,
            comment,
            object,
            states,
            check_existence,
            state_operator,
            deprecated,
            notes,
            signature,
        )


# RPMVerifyFile classes
@dataclass
class RpmVerifyFileBehaviors:
    nolinkto: Optional[bool] = None
    nomd5: Optional[bool] = None
    nosize: Optional[bool] = None
    nouser: Optional[bool] = None
    nogroup: Optional[bool] = None
    nomtime: Optional[bool] = None
    nomode: Optional[bool] = None
    nordev: Optional[bool] = None
    noconfigfiles: Optional[bool] = None
    noghostfiles: Optional[bool] = None
    _tag = "behaviors"

    def to_xml(self) -> xml.Element:
        r = xml.Element(self._tag)
        if self.nolinkto is not None:
            r.set("nolinkto", bool_to_xml(self.nolinkto))
        if self.nomd5 is not None:
            r.set("nomd5", bool_to_xml(self.nomd5))
        if self.nosize is not None:
            r.set("nosize", bool_to_xml(self.nosize))
        if self.nouser is not None:
            r.set("nouser", bool_to_xml(self.nouser))
        if self.nogroup is not None:
            r.set("nogroup", bool_to_xml(self.nogroup))
        if self.nomtime is not None:
            r.set("nomtime", bool_to_xml(self.nomtime))
        if self.nomode is not None:
            r.set("nomode", bool_to_xml(self.nomode))
        if self.nordev is not None:
            r.set("nordev", bool_to_xml(self.nordev))
        if self.noconfigfiles is not None:
            r.set("noconfigfiles", bool_to_xml(self.noconfigfiles))
        if self.noghostfiles is not None:
            r.set("noghostfiles", bool_to_xml(self.noghostfiles))
        return r


@dataclass
class RPMVerifyFileObject(ObjectType):
    name: EntityObjectStringType = None  # type: ignore
    epoch: EntityObjectAnySimpleType = None  # type: ignore
    file_version: EntityObjectAnySimpleType = None  # type: ignore
    release: EntityObjectAnySimpleType = None  # type: ignore
    arch: EntityObjectStringType = None  # type: ignore
    filepath: EntityObjectStringType = None  # type: ignore
    behaviors: Optional[RpmVerifyFileBehaviors] = None
    filters: Optional[list[Filter]] = None

    def __init__(
        self,
        *,
        id: str,
        version: int,
        name: EntityObjectStringType,
        epoch: EntityObjectAnySimpleType,
        file_version: EntityObjectAnySimpleType,
        release: EntityObjectAnySimpleType,
        arch: EntityObjectStringType,
        filepath: EntityObjectStringType,
        behaviors: Optional[RpmVerifyFileBehaviors] = None,
        filters: Optional[list[Filter]] = None,
        comment: Optional[str] = None,
        deprecated: Optional[bool] = None,
        notes: Optional[NotesType] = None,
        signature: Optional[Signature] = None,
    ):
        self.name = name
        self.epoch = epoch
        self.file_version = file_version
        self.release = release
        self.arch = arch
        self.filepath = filepath
        self.behaviors = behaviors
        self.filters = filters
        super().__init__(
            "rpmverifyfile_object",
            id,
            version,
            comment,
            deprecated,
            notes,
            signature,
        )

    def to_xml(self) -> xml.Element:
        r = super().to_xml()

        if self.behaviors is not None:
            r.append(self.behaviors.to_xml())
        if self.name is not None:
            r.append(self.name.to_xml())
        if self.epoch is not None:
            # special case for  epoch value `0` to comply with `rpm -q --qf '%{EPOCH}\n'` result
            if self.epoch.value == "0":
                self.epoch.value = "(none)"
            r.append(self.epoch.to_xml())
        if self.file_version is not None:
            r.append(self.file_version.to_xml())
        if self.release is not None:
            r.append(self.release.to_xml())
        if self.arch is not None:
            r.append(self.arch.to_xml())
        if self.filepath is not None:
            r.append(self.filepath.to_xml())
        if self.filters:
            for fl in self.filters:
                r.append(fl.to_xml())

        return r


@dataclass
class RPMVerifyFileState(StateType):
    name: Optional[EntityStateStringType] = None
    epoch: Optional[EntityStateAnySimpleType] = None
    file_version: Optional[EntityStateAnySimpleType] = None
    release: Optional[EntityStateAnySimpleType] = None
    arch: Optional[EntityStateStringType] = None
    filepath: Optional[EntityStateStringType] = None
    extended_name: Optional[EntityStateStringType] = None
    size_differs: Optional[EntityStateRpmVerifyResultType] = None
    mode_differs: Optional[EntityStateRpmVerifyResultType] = None
    md5_differs: Optional[EntityStateRpmVerifyResultType] = None
    device_differs: Optional[EntityStateRpmVerifyResultType] = None
    link_mismatch: Optional[EntityStateRpmVerifyResultType] = None
    ownership_differs: Optional[EntityStateRpmVerifyResultType] = None
    group_differs: Optional[EntityStateRpmVerifyResultType] = None
    mtime_differs: Optional[EntityStateRpmVerifyResultType] = None
    capabilities_differ: Optional[EntityStateRpmVerifyResultType] = None
    configuration_file: Optional[EntityStateBoolType] = None
    documentation_file: Optional[EntityStateBoolType] = None
    ghost_file: Optional[EntityStateBoolType] = None
    license_file: Optional[EntityStateBoolType] = None
    readme_file: Optional[EntityStateBoolType] = None

    def __init__(
        self,
        *,
        id: str,
        version: int,
        name: Optional[EntityStateStringType] = None,
        epoch: Optional[EntityStateAnySimpleType] = None,
        file_version: Optional[EntityStateAnySimpleType] = None,
        release: Optional[EntityStateAnySimpleType] = None,
        arch: Optional[EntityStateStringType] = None,
        filepath: Optional[EntityStateStringType] = None,
        extended_name: Optional[EntityStateStringType] = None,
        size_differs: Optional[EntityStateRpmVerifyResultType] = None,
        mode_differs: Optional[EntityStateRpmVerifyResultType] = None,
        md5_differs: Optional[EntityStateRpmVerifyResultType] = None,
        device_differs: Optional[EntityStateRpmVerifyResultType] = None,
        link_mismatch: Optional[EntityStateRpmVerifyResultType] = None,
        ownership_differs: Optional[EntityStateRpmVerifyResultType] = None,
        group_differs: Optional[EntityStateRpmVerifyResultType] = None,
        mtime_differs: Optional[EntityStateRpmVerifyResultType] = None,
        capabilities_differ: Optional[EntityStateRpmVerifyResultType] = None,
        configuration_file: Optional[EntityStateBoolType] = None,
        documentation_file: Optional[EntityStateBoolType] = None,
        ghost_file: Optional[EntityStateBoolType] = None,
        license_file: Optional[EntityStateBoolType] = None,
        readme_file: Optional[EntityStateBoolType] = None,
        comment: Optional[str] = None,
        operator: Optional[OperatorEnumeration] = None,
        deprecated: Optional[bool] = None,
        notes: Optional[NotesType] = None,
        signature: Optional[Signature] = None,
    ):
        self.name = name
        self.epoch = epoch
        self.file_version = file_version
        self.release = release
        self.arch = arch
        self.filepath = filepath
        self.extended_name = extended_name
        self.size_differs = size_differs
        self.mode_differs = mode_differs
        self.md5_differs = md5_differs
        self.device_differs = device_differs
        self.link_mismatch = link_mismatch
        self.ownership_differs = ownership_differs
        self.group_differs = group_differs
        self.mtime_differs = mtime_differs
        self.capabilities_differ = capabilities_differ
        self.configuration_file = configuration_file
        self.documentation_file = documentation_file
        self.ghost_file = ghost_file
        self.license_file = license_file
        readme_file = readme_file

        super().__init__(
            "rpmverifyfile_state",
            id,
            version,
            comment,
            operator,
            deprecated,
            notes,
            signature,
        )

    def to_xml(self) -> xml.Element:
        r = super().to_xml()

        if self.name is not None:
            r.append(self.name.to_xml())
        if self.epoch is not None:
            # special case for  epoch value `0` to comply with `rpm -q --qf '%{EPOCH}\n'` result
            if self.epoch.value == "0":
                self.epoch.value = "(none)"
            r.append(self.epoch.to_xml())
        if self.file_version is not None:
            r.append(self.file_version.to_xml())
        if self.release is not None:
            r.append(self.release.to_xml())
        if self.arch is not None:
            r.append(self.arch.to_xml())
        if self.filepath is not None:
            r.append(self.filepath.to_xml())
        if self.extended_name is not None:
            r.append(self.extended_name.to_xml())
        if self.size_differs is not None:
            r.append(self.size_differs.to_xml())
        if self.mode_differs is not None:
            r.append(self.mode_differs.to_xml())
        if self.md5_differs is not None:
            r.append(self.md5_differs.to_xml())
        if self.device_differs is not None:
            r.append(self.device_differs.to_xml())
        if self.link_mismatch is not None:
            r.append(self.link_mismatch.to_xml())
        if self.ownership_differs is not None:
            r.append(self.ownership_differs.to_xml())
        if self.group_differs is not None:
            r.append(self.group_differs.to_xml())
        if self.mtime_differs is not None:
            r.append(self.mtime_differs.to_xml())
        if self.capabilities_differ is not None:
            r.append(self.capabilities_differ.to_xml())
        if self.configuration_file is not None:
            r.append(self.configuration_file.to_xml())
        if self.documentation_file is not None:
            r.append(self.documentation_file.to_xml())
        if self.ghost_file is not None:
            r.append(self.ghost_file.to_xml())
        if self.license_file is not None:
            r.append(self.license_file.to_xml())
        if self.readme_file is not None:
            r.append(self.readme_file.to_xml())

        return r


@dataclass
class RPMVerifyFileTest(TestType):
    def __init__(
        self,
        *,
        id: str,
        version: int,
        check: CheckEnumeration,
        comment: str,
        object: ObjectRefType,
        states: Optional[list[StateRefType]] = None,
        check_existence: Optional[ExistenceEnumeration] = None,
        state_operator: Optional[OperatorEnumeration] = None,
        deprecated: Optional[bool] = None,
        notes: Optional[NotesType] = None,
        signature: Optional[Signature] = None,
    ):
        super().__init__(
            "rpmverifyfile_test",
            id,
            version,
            check,
            comment,
            object,
            states,
            check_existence,
            state_operator,
            deprecated,
            notes,
            signature,
        )


# RPMVerifyPackage classes
@dataclass
class RpmVerifyPackageBehaviors:
    nodeps: Optional[bool] = None
    noscripts: Optional[bool] = None
    _tag = "behaviors"

    def to_xml(self) -> xml.Element:
        r = xml.Element(self._tag)
        if self.nodeps is not None:
            r.set("nodeps", bool_to_xml(self.nodeps))
        if self.noscripts is not None:
            r.set("noscripts", bool_to_xml(self.noscripts))
        return r


@dataclass
class RPMVerifyPackageObject(ObjectType):
    name: EntityObjectStringType = None  # type: ignore
    epoch: EntityObjectAnySimpleType = None  # type: ignore
    pkg_version: EntityObjectAnySimpleType = None  # type: ignore
    release: EntityObjectAnySimpleType = None  # type: ignore
    arch: EntityObjectStringType = None  # type: ignore
    behaviors: Optional[RpmVerifyPackageBehaviors] = None
    filters: Optional[list[Filter]] = None

    def __init__(
        self,
        *,
        id: str,
        version: int,
        name: EntityObjectStringType,
        epoch: EntityObjectAnySimpleType,
        pkg_version: EntityObjectAnySimpleType,
        release: EntityObjectAnySimpleType,
        arch: EntityObjectStringType,
        behaviors: Optional[RpmVerifyPackageBehaviors] = None,
        filters: Optional[list[Filter]] = None,
        comment: Optional[str] = None,
        deprecated: Optional[bool] = None,
        notes: Optional[NotesType] = None,
        signature: Optional[Signature] = None,
    ):
        self.name = name
        self.epoch = epoch
        self.pkg_version = pkg_version
        self.release = release
        self.arch = arch
        self.behaviors = behaviors
        self.filters = filters
        super().__init__(
            "rpmverifypackage_object",
            id,
            version,
            comment,
            deprecated,
            notes,
            signature,
        )

    def to_xml(self) -> xml.Element:
        r = super().to_xml()

        if self.behaviors is not None:
            r.append(self.behaviors.to_xml())
        if self.name is not None:
            r.append(self.name.to_xml())
        if self.epoch is not None:
            # special case for  epoch value `0` to comply with `rpm -q --qf '%{EPOCH}\n'` result
            if self.epoch.value == "0":
                self.epoch.value = "(none)"
            r.append(self.epoch.to_xml())
        if self.pkg_version is not None:
            r.append(self.pkg_version.to_xml())
        if self.release is not None:
            r.append(self.release.to_xml())
        if self.arch is not None:
            r.append(self.arch.to_xml())
        if self.filters:
            for fl in self.filters:
                r.append(fl.to_xml())

        return r


@dataclass
class RPMVerifyPackageState(StateType):
    name: Optional[EntityStateStringType] = None
    epoch: Optional[EntityStateAnySimpleType] = None
    pkg_version: Optional[EntityStateAnySimpleType] = None
    release: Optional[EntityStateAnySimpleType] = None
    arch: Optional[EntityStateStringType] = None
    extended_name: Optional[EntityStateStringType] = None
    dependency_check_passed: Optional[EntityStateBoolType] = None
    verification_script_successful: Optional[EntityStateBoolType] = None

    def __init__(
        self,
        *,
        id: str,
        version: int,
        name: Optional[EntityStateStringType] = None,
        epoch: Optional[EntityStateAnySimpleType] = None,
        pkg_version: Optional[EntityStateAnySimpleType] = None,
        release: Optional[EntityStateAnySimpleType] = None,
        arch: Optional[EntityStateStringType] = None,
        extended_name: Optional[EntityStateStringType] = None,
        dependency_check_passed: Optional[EntityStateBoolType] = None,
        verification_script_successful: Optional[EntityStateBoolType] = None,
        comment: Optional[str] = None,
        operator: Optional[OperatorEnumeration] = None,
        deprecated: Optional[bool] = None,
        notes: Optional[NotesType] = None,
        signature: Optional[Signature] = None,
    ):
        self.name = name
        self.epoch = epoch
        self.pkg_version = pkg_version
        self.release = release
        self.arch = arch
        self.extended_name = extended_name
        self.dependency_check_passed = dependency_check_passed
        self.verification_script_successful = verification_script_successful
        super().__init__(
            "rpmverifypackage_state",
            id,
            version,
            comment,
            operator,
            deprecated,
            notes,
            signature,
        )

    def to_xml(self) -> xml.Element:
        r = super().to_xml()

        if self.name is not None:
            r.append(self.name.to_xml())
        if self.epoch is not None:
            # special case for  epoch value `0` to comply with `rpm -q --qf '%{EPOCH}\n'` result
            if self.epoch.value == "0":
                self.epoch.value = "(none)"
            r.append(self.epoch.to_xml())
        if self.pkg_version is not None:
            r.append(self.pkg_version.to_xml())
        if self.release is not None:
            r.append(self.release.to_xml())
        if self.arch is not None:
            r.append(self.arch.to_xml())
        if self.extended_name is not None:
            r.append(self.extended_name.to_xml())
        if self.dependency_check_passed is not None:
            r.append(self.dependency_check_passed.to_xml())
        if self.verification_script_successful is not None:
            r.append(self.verification_script_successful.to_xml())

        return r


@dataclass
class RPMVerifyPackageTest(TestType):
    def __init__(
        self,
        *,
        id: str,
        version: int,
        check: CheckEnumeration,
        comment: str,
        object: ObjectRefType,
        states: Optional[list[StateRefType]] = None,
        check_existence: Optional[ExistenceEnumeration] = None,
        state_operator: Optional[OperatorEnumeration] = None,
        deprecated: Optional[bool] = None,
        notes: Optional[NotesType] = None,
        signature: Optional[Signature] = None,
    ):
        super().__init__(
            "rpmverifypackage_test",
            id,
            version,
            check,
            comment,
            object,
            states,
            check_existence,
            state_operator,
            deprecated,
            notes,
            signature,
        )
