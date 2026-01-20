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

from dataclasses import dataclass, fields
from typing import Any, Literal, Optional, Union

from .enumeration import (
    CheckEnumeration,
    DatatypeEnumeration,
    OperationEnumeration,
    SimpleDatatypeEnumeration,
    check_val_in_enum,
)
from .pattern import reVariableIDPattern
from .utils import bool_to_xml


def to_xml_attribute(val: Any) -> Union[str, None]:
    if val is None:
        return None
    # handle enum's
    if hasattr(val, "value"):
        return val.value
    # convert boolean
    if isinstance(val, bool):
        return bool_to_xml(val)
    # default
    return str(val)


# Entity base classes
@dataclass
class EntityAttributeGroup:
    datatype: Union[DatatypeEnumeration, SimpleDatatypeEnumeration, None] = None
    operation: Optional[OperationEnumeration] = None
    mask: Optional[bool] = None
    var_ref: Optional[str] = None  # should match VariableIDPattern
    var_check: Optional[CheckEnumeration] = None

    def __post_init__(self):
        if self.var_ref is not None and not reVariableIDPattern.match(self.var_ref):
            raise ValueError(
                f"var_ref [{self.var_ref}] doesn't match with VariableIDPattern"
            )

        if self.datatype is not None and not check_val_in_enum(
            self.datatype.value, DatatypeEnumeration
        ):
            raise ValueError(f"datatype [{self.datatype}] not in DatatypeEnumeration")

        if self.operation is not None and not check_val_in_enum(
            self.operation.value, OperationEnumeration
        ):
            raise ValueError(
                f"operation [{self.operation}] not in OperationEnumeration"
            )

        if self.var_check is not None and not check_val_in_enum(
            self.var_check.value, CheckEnumeration
        ):
            raise ValueError(f"var_check [{self.var_check}] not in CheckEnumeration")


@dataclass
class EntitySimpleBaseType:
    attributes: EntityAttributeGroup
    value: Optional[str] = None
    tag = ""

    def to_xml(self) -> xml.Element:
        r = xml.Element(self.tag)
        for attr in [f.name for f in fields(self.attributes)]:
            try:
                v = to_xml_attribute(self.attributes.__getattribute__(attr))
            except AttributeError:
                v = None

            if v is not None:
                r.set(attr, v)

        if self.value is not None:
            r.text = self.value

        return r


@dataclass
class EntityComplexBaseType:
    attributes: EntityAttributeGroup
    tag = ""

    def to_xml(self) -> xml.Element:
        r = xml.Element(self.tag)
        for attr in [f.name for f in fields(self.attributes)]:
            try:
                v = to_xml_attribute(self.attributes.__getattribute__(attr))
            except AttributeError:
                v = None

            if v is not None:
                r.set(attr, v)

        return r


# EntityObject classes
@dataclass
class EntityObjectAnySimpleType(EntitySimpleBaseType):
    def __init__(
        self, tag: str, datatype: SimpleDatatypeEnumeration, value: Optional[str]
    ):
        self.attributes = EntityAttributeGroup(datatype=datatype)
        self.value = value
        self.tag = tag


@dataclass
class EntityObjectBinaryType(EntitySimpleBaseType):
    def __init__(self, tag: str, value: Optional[str]):
        self.attributes = EntityAttributeGroup(
            datatype=SimpleDatatypeEnumeration.binary
        )
        self.value = value
        self.tag = tag


@dataclass
class EntityObjectBoolType(EntitySimpleBaseType):
    def __init__(self, tag: str, value: Optional[str]):
        self.attributes = EntityAttributeGroup(
            datatype=SimpleDatatypeEnumeration.boolean
        )
        self.value = value
        self.tag = tag


@dataclass
class EntityObjectFloatType(EntitySimpleBaseType):
    def __init__(self, tag: str, value: Optional[str]):
        self.attributes = EntityAttributeGroup(datatype=SimpleDatatypeEnumeration.float)
        self.value = value
        self.tag = tag


@dataclass
class EntityObjectIntType(EntitySimpleBaseType):
    def __init__(self, tag: str, value: Optional[str]):
        self.attributes = EntityAttributeGroup(datatype=SimpleDatatypeEnumeration.int)
        self.value = value
        self.tag = tag


@dataclass
class EntityObjectStringType(EntitySimpleBaseType):
    def __init__(self, tag: str, value: Optional[str]):
        self.attributes = EntityAttributeGroup(
            datatype=SimpleDatatypeEnumeration.string
        )
        self.value = value
        self.tag = tag


@dataclass
class EntityObjectFieldType:
    tag: str
    name: str
    attributes: EntityAttributeGroup
    value: Optional[str] = None

    def to_xml(self) -> xml.Element:
        r = xml.Element(self.tag)
        r.set("name", self.name)

        for attr in [f.name for f in fields(self.attributes)]:
            try:
                v = to_xml_attribute(self.attributes.__getattribute__(attr))
            except AttributeError:
                v = None

            if v is not None:
                r.set(attr, v)

        if self.value is not None:
            r.text = self.value

        return r


@dataclass
class EntityObjectRecordType(EntityComplexBaseType):
    def __init__(
        self,
        tag: str,
        fields: list[EntityObjectFieldType],
        mask: Optional[bool] = None,
        var_ref: Optional[str] = None,
        var_check: Optional[CheckEnumeration] = None,
    ):
        self.attributes = EntityAttributeGroup(
            datatype=DatatypeEnumeration.record,
            operation=OperationEnumeration.equals,
            mask=mask,
            var_ref=var_ref,
            var_check=var_check,
        )
        self.fields = fields
        self.tag = tag

    def to_xml(self) -> xml.Element:
        r = super().to_xml()
        for fl in self.fields:
            r.append(fl.to_xml())
        return r


# EntityState classes
@dataclass
class EntityStateSimpleBaseType(EntitySimpleBaseType):
    def __init__(
        self,
        tag: str,
        datatype: SimpleDatatypeEnumeration,
        value: Optional[str],
        entity_check: Optional[CheckEnumeration],
    ):
        self.attributes = EntityAttributeGroup(datatype=datatype)
        self.value = value
        self.entity_check = entity_check
        self.tag = tag

    def to_xml(self) -> xml.Element:
        r = super().to_xml()
        if self.entity_check is not None:
            r.set("entity_check", self.entity_check.value)
        return r


@dataclass
class EntityStateComplexBaseType(EntitySimpleBaseType):
    def __init__(
        self,
        tag: str,
        datatype: SimpleDatatypeEnumeration,
        entity_check: Optional[CheckEnumeration],
    ):
        self.attributes = EntityAttributeGroup(datatype=datatype)
        self.value = None
        self.entity_check = entity_check
        self.tag = tag

    def to_xml(self) -> xml.Element:
        r = super().to_xml()
        if self.entity_check is not None:
            r.set("entity_check", self.entity_check.value)
        return r


@dataclass
class EntityStateAnySimpleType(EntityStateSimpleBaseType):
    def __init__(
        self,
        tag: str,
        value: Optional[str],
        datatype: Optional[SimpleDatatypeEnumeration],
        entity_check: Optional[CheckEnumeration],
    ):
        if datatype is not None:
            self.attributes = EntityAttributeGroup(datatype=datatype)
        else:
            self.attributes = EntityAttributeGroup()
        self.value = value
        self.entity_check = entity_check
        self.tag = tag

    def to_xml(self) -> xml.Element:
        r = super().to_xml()
        if self.entity_check is not None:
            r.set("entity_check", self.entity_check.value)
        return r


@dataclass
class EntityStateBinaryType(EntityStateSimpleBaseType):
    def __init__(
        self,
        tag: str,
        value: Optional[str],
        entity_check: Optional[CheckEnumeration],
    ):
        self.attributes = EntityAttributeGroup(
            datatype=SimpleDatatypeEnumeration.binary
        )
        self.value = value
        self.entity_check = entity_check
        self.tag = tag


@dataclass
class EntityStateBoolType(EntityStateSimpleBaseType):
    def __init__(
        self,
        tag: str,
        value: Optional[str],
        entity_check: Optional[CheckEnumeration],
    ):
        self.attributes = EntityAttributeGroup(
            datatype=SimpleDatatypeEnumeration.boolean
        )
        self.value = value
        self.entity_check = entity_check
        self.tag = tag


@dataclass
class EntityStateFloatType(EntityStateSimpleBaseType):
    def __init__(
        self,
        tag: str,
        value: Optional[str],
        entity_check: Optional[CheckEnumeration],
    ):
        self.attributes = EntityAttributeGroup(datatype=SimpleDatatypeEnumeration.float)
        self.value = value
        self.entity_check = entity_check
        self.tag = tag


@dataclass
class EntityStateIntType(EntityStateSimpleBaseType):
    def __init__(
        self,
        tag: str,
        value: Optional[str],
        entity_check: Optional[CheckEnumeration],
    ):
        self.attributes = EntityAttributeGroup(datatype=SimpleDatatypeEnumeration.int)
        self.value = value
        self.entity_check = entity_check
        self.tag = tag


@dataclass
class EntityStateStringType(EntityStateSimpleBaseType):
    def __init__(
        self,
        tag: str,
        value: Optional[str],
        entity_check: Optional[CheckEnumeration],
    ):
        self.attributes = EntityAttributeGroup(
            datatype=SimpleDatatypeEnumeration.string
        )
        self.value = value
        self.entity_check = entity_check
        self.tag = tag


@dataclass
class EntityStateEVRStringType(EntityStateSimpleBaseType):
    def __init__(
        self,
        tag: str,
        value: Optional[str],
        entity_check: Optional[CheckEnumeration],
    ):
        self.attributes = EntityAttributeGroup(
            datatype=SimpleDatatypeEnumeration.evr_string
        )
        self.value = value
        self.entity_check = entity_check
        self.tag = tag


@dataclass
class EntityStateVersionType(EntityStateSimpleBaseType):
    def __init__(
        self,
        tag: str,
        value: Optional[str],
        entity_check: Optional[CheckEnumeration],
    ):
        self.attributes = EntityAttributeGroup(
            datatype=SimpleDatatypeEnumeration.version
        )
        self.value = value
        self.entity_check = entity_check
        self.tag = tag


@dataclass
class EntityStateFileSetRevisionType(EntityStateSimpleBaseType):
    def __init__(
        self,
        tag: str,
        value: Optional[str],
        entity_check: Optional[CheckEnumeration],
    ):
        self.attributes = EntityAttributeGroup(
            datatype=SimpleDatatypeEnumeration.fileset_revision
        )
        self.value = value
        self.entity_check = entity_check
        self.tag = tag


@dataclass
class EntityStateFieldType:
    tag: str
    name: str
    attributes: EntityAttributeGroup
    entity_check: Optional[CheckEnumeration] = None
    value: Optional[str] = None

    def to_xml(self) -> xml.Element:
        r = xml.Element(self.tag)
        r.set("name", self.name)

        for attr in [f.name for f in fields(self.attributes)]:
            try:
                v = to_xml_attribute(self.attributes.__getattribute__(attr))
            except AttributeError:
                v = None

            if v is not None:
                r.set(attr, v)

        if self.entity_check is not None:
            r.set("entity_check", self.entity_check.value)

        if self.value is not None:
            r.text = self.value

        return r


@dataclass
class EntityStateRecordType(EntityStateComplexBaseType):
    def __init__(
        self,
        tag: str,
        fields: list[EntityObjectFieldType],
        mask: Optional[bool] = None,
        var_ref: Optional[str] = None,
        var_check: Optional[CheckEnumeration] = None,
    ):
        self.attributes = EntityAttributeGroup(
            datatype=DatatypeEnumeration.record,
            operation=OperationEnumeration.equals,
            mask=mask,
            var_ref=var_ref,
            var_check=var_check,
        )
        self.fields = fields
        self.tag = tag

    def to_xml(self) -> xml.Element:
        r = super().to_xml()
        for fl in self.fields:
            r.append(fl.to_xml())
        return r


@dataclass
class EntityStateRpmVerifyResultType(EntityObjectStringType):
    def __init__(
        self, tag: str, value: Union[Literal["pass", "fail", "not performed"], None]
    ):
        super().__init__(tag, value)
