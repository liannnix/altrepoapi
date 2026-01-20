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
from datetime import datetime
from typing import Any, NamedTuple, Optional

from .enumeration import (
    CheckEnumeration,
    ClassEnumeration,
    SimpleDatatypeEnumeration,
    ExistenceEnumeration,
    FamilyEnumeration,
    FilterActionEnumeration,
    OperatorEnumeration,
    check_val_in_enum,
)
from .pattern import (
    DefinitionIDPattern,
    VariableIDPattern,
    ObjectIDPattern,
    StateIDPattern,
    TestIDPattern,
    reDefinitionIDPattern,
    reObjectIDPattern,
    reStateIDPattern,
    reTestIDPattern,
)
from .utils import bool_to_xml, extension_point_to_xml, make_sub_element
from . import ns


class NonEmptyStringType(str):
    def __new__(cls, s: str):
        if not isinstance(s, str) or s == "":
            raise ValueError("Should be not empty string")
        instance = super().__new__(cls, s)
        return instance


class UnsignedInteger(int):
    def __new__(cls, value: int):
        if not isinstance(value, int) or value < 0:
            raise ValueError("Should be unsigned integer")
        instance = super().__new__(cls, value)
        return instance


class Signature(NamedTuple):
    value: str
    _tag = "ext:Signature"

    def to_xml(self) -> xml.Element:
        r = xml.Element(self._tag)
        r.text = self.value
        return r


@dataclass
class Filter:
    value: StateIDPattern
    action: Optional[FilterActionEnumeration] = None
    _tag = "filter"

    def __post_init__(self):
        if not reStateIDPattern.match(self.value):
            raise ValueError(f"value {self.value} doesn't match with StateIDPattern")

        if self.action is not None and not check_val_in_enum(
            self.action.value, FilterActionEnumeration
        ):
            raise ValueError(f"action [{self.action}] not in FilterActionEnumeration")

    def to_xml(self):
        r = xml.Element(self._tag)
        if self.action:
            r.set("action", self.action.value)
        r.text = self.value
        return r


@dataclass
class GeneratorType:
    timestamp: datetime
    product_name: Optional[str] = None
    product_version: Optional[str] = None
    schema_version: str = "5.11"
    extension_point: Any = None
    _tag = "generator"

    def to_xml(self) -> xml.Element:
        r = xml.Element(self._tag)
        for field in fields(self):
            if field.name == "_tag":
                continue

            try:
                v = self.__getattribute__(field.name)
            except AttributeError:
                continue

            if v is None:
                continue

            if isinstance(v, datetime):
                v = v.isoformat()

            if hasattr(v, "to_xml"):
                r.append(v.to_xml())  # type: ignore
            else:
                make_sub_element(r, f"oval:{field.name}", v)

        return r


@dataclass
class AffectedType:
    family: FamilyEnumeration
    platform: Optional[list[str]] = None
    product: Optional[list[str]] = None
    _tag = "affected"

    def __post_init__(self):
        if not check_val_in_enum(self.family.value, FamilyEnumeration):
            raise ValueError(f"family [{self.family}] not in FamilyEnumeration")

    def to_xml(self) -> xml.Element:
        r = xml.Element(self._tag)
        r.set("family", self.family.value)

        if self.platform:
            for p in self.platform:
                make_sub_element(r, "platform", p)

        if self.product:
            for p in self.product:
                make_sub_element(r, "product", p)

        return r


@dataclass
class ReferenceType:
    source: str
    ref_id: str
    ref_url: Optional[str] = None
    _tag = "reference"

    def to_xml(self) -> xml.Element:
        r = xml.Element(self._tag)

        r.set("ref_id", self.ref_id)
        if self.ref_url:
            r.set("ref_url", self.ref_url)
        r.set("source", self.source)

        return r


@dataclass
class NotesType:
    notes: Optional[list[str]] = None
    _tag = "notes"

    def to_xml(self) -> xml.Element:
        r = xml.Element(self._tag)

        if self.notes:
            for note in self.notes:
                make_sub_element(r, "note", note)

        return r


@dataclass
class MetadataType:
    title: str
    description: str
    affected: Optional[list[AffectedType]] = None
    references: Optional[list[ReferenceType]] = None
    extension_point: Any = None
    _tag = "metadata"

    def to_xml(self) -> xml.Element:
        r = xml.Element(self._tag)

        make_sub_element(r, "title", self.title)

        if self.affected:
            for af in self.affected:
                r.append(af.to_xml())

        if self.references:
            for rs in self.references:
                r.append(rs.to_xml())

        make_sub_element(r, "description", self.description)

        if self.extension_point is not None:
            r.append(extension_point_to_xml(self.extension_point))

        return r


@dataclass
class ExtendDefinitionType:
    definition_ref: DefinitionIDPattern
    negate: Optional[bool] = None
    comment: Optional[str] = None
    applicability_check: Optional[bool] = None
    _tag = "extend_definition"

    def __post_init__(self):
        if not reDefinitionIDPattern.match(self.definition_ref):
            raise ValueError(
                f"definition_ref {self.definition_ref} doesn't match with DefinitionIDPattern"
            )

        if self.comment is not None:
            self.comment = NonEmptyStringType(self.comment)

    def to_xml(self) -> xml.Element:
        r = xml.Element(self._tag)

        r.set("definition_ref", self.definition_ref)

        if self.negate is not None:
            r.set("negate", bool_to_xml(self.negate))

        if self.comment is not None:
            r.set("comment", self.comment)

        if self.applicability_check is not None:
            r.set("applicability_check", bool_to_xml(self.applicability_check))

        return r


@dataclass
class CriterionType:
    test_ref: TestIDPattern
    negate: Optional[bool] = None
    comment: Optional[str] = None
    applicability_check: Optional[bool] = None
    _tag = "criterion"

    def __post_init__(self):
        if not reTestIDPattern.match(self.test_ref):
            raise ValueError(
                f"test_ref {self.test_ref} doesn't match with TestIDPattern"
            )

        if self.comment is not None:
            self.comment = NonEmptyStringType(self.comment)

    def to_xml(self) -> xml.Element:
        r = xml.Element(self._tag)

        r.set("test_ref", self.test_ref)

        if self.negate is not None:
            r.set("negate", bool_to_xml(self.negate))

        if self.comment is not None:
            r.set("comment", self.comment)

        if self.applicability_check is not None:
            r.set("applicability_check", bool_to_xml(self.applicability_check))

        return r


@dataclass
class CriteriaType:
    operator: Optional[OperatorEnumeration] = None
    negate: Optional[bool] = None
    comment: Optional[str] = None
    criterias: Optional[list["CriteriaType"]] = None
    criterions: Optional[list[CriterionType]] = None
    extend_definitions: Optional[list[ExtendDefinitionType]] = None
    applicability_check: Optional[bool] = None
    _tag = "criteria"

    def __post_init__(self):
        if self.operator is not None and not check_val_in_enum(
            self.operator.value, OperatorEnumeration
        ):
            raise ValueError(f"operator [{self.operator}] not in OperatorEnumeration")

        if self.comment is not None:
            self.comment = NonEmptyStringType(self.comment)

    def to_xml(self) -> xml.Element:
        r = xml.Element(self._tag)

        if self.operator:
            r.set("operator", self.operator.value)

        if self.negate is not None:
            r.set("negate", bool_to_xml(self.negate))

        if self.comment is not None:
            r.set("comment", self.comment)

        if self.applicability_check is not None:
            r.set("applicability_check", bool_to_xml(self.applicability_check))

        if self.criterions:
            for crn in self.criterions:
                r.append(crn.to_xml())

        if self.criterias:
            for cra in self.criterias:
                r.append(cra.to_xml())

        if self.extend_definitions:
            for exd in self.extend_definitions:
                r.append(exd.to_xml())

        return r


@dataclass
class DefinitionType:
    id: DefinitionIDPattern
    version: int
    class_: ClassEnumeration
    metadata: MetadataType
    deprecated: Optional[bool] = None
    notes: Optional[NotesType] = None
    criteria: Optional[CriteriaType] = None
    signature: Optional[Signature] = None
    _tag = "definition"

    def __post_init__(self):
        if not reDefinitionIDPattern.match(self.id):
            raise ValueError(f"id [{self.id}] doesn't match with DefinitionIDPattern")

        self.version = UnsignedInteger(self.version)

        if not check_val_in_enum(self.class_.value, ClassEnumeration):
            raise ValueError(f"class [{self.class_}] not in CLassEnumeration")

    def to_xml(self) -> xml.Element:
        r = xml.Element(self._tag)

        r.set("id", self.id)
        r.set("version", str(self.id))
        r.set("class", self.class_.value)

        if self.deprecated is not None:
            r.set("deprecated", bool_to_xml(self.deprecated))

        r.append(self.metadata.to_xml())

        if self.notes:
            r.append(self.notes.to_xml())

        if self.criteria:
            r.append(self.criteria.to_xml())

        if self.signature:
            r.append(self.signature.to_xml())

        return r


@dataclass
class DefinitionsType:
    definitions: list[DefinitionType]
    _tag = "definitions"

    def to_xml(self) -> xml.Element:
        r = xml.Element(self._tag)

        for d in self.definitions:
            r.append(d.to_xml())

        return r


@dataclass
class VariableType:
    """Base OVAL Definitions::VariableType"""

    tag: str  # XXX: should be set properly
    id: VariableIDPattern
    version: int
    datatype: SimpleDatatypeEnumeration
    comment: str
    deprecated: Optional[bool] = None
    notes: Optional[NotesType] = None
    signature: Optional[Signature] = None

    def __post_init__(self):
        self.tag = NonEmptyStringType(self.tag)
        self.version = UnsignedInteger(self.version)
        self.comment = NonEmptyStringType(self.comment)

    def to_xml(self) -> xml.Element:
        r = xml.Element(self.tag)

        r.set("id", self.id)
        r.set("version", str(self.version))
        r.set("datatype", self.datatype.value)
        r.set("comment", self.comment)

        if self.deprecated is not None:
            r.set("deprecated", bool_to_xml(self.deprecated))

        # FIXME: need to verify this behavior with some real world example!
        # for val in self.values:
        #     r.append(value_to_xml(val, "value"))

        if self.notes:
            r.append(self.notes.to_xml())

        if self.signature:
            r.append(self.signature.to_xml())

        return r


@dataclass
class VariablesType:
    variables: list[VariableType]
    _tag = "variables"

    def to_xml(self) -> xml.Element:
        r = xml.Element(self._tag)

        for v in self.variables:
            r.append(v.to_xml())

        return r


@dataclass
class StateRefType:
    state_ref: StateIDPattern
    _tag = "state"

    def __post_init__(self):
        if not reStateIDPattern.match(self.state_ref):
            raise ValueError(
                f"state_ref [{self.state_ref}] doesn't match with StateIDPattern"
            )

    def to_xml(self) -> xml.Element:
        r = xml.Element(self._tag)
        r.set("state_ref", self.state_ref)
        return r


@dataclass
class StateType:
    """Base OVAL Definitions::StateType"""

    tag: str  # XXX: should be set properly
    id: StateIDPattern
    version: int
    comment: Optional[str] = None
    operator: Optional[OperatorEnumeration] = None
    deprecated: Optional[bool] = None
    notes: Optional[NotesType] = None
    signature: Optional[Signature] = None

    def __post_init__(self):
        self.tag = NonEmptyStringType(self.tag)
        self.version = UnsignedInteger(self.version)

        if self.comment is not None:
            self.comment = NonEmptyStringType(self.comment)

        if not reStateIDPattern.match(self.id):
            raise ValueError(f"id [{self.id}] doesn't match with StateIDPattern")

        if self.operator is not None and not check_val_in_enum(
            self.operator.value, OperatorEnumeration
        ):
            raise ValueError(f"operator [{self.operator}] not in OperatorEnumeration")

    def to_xml(self) -> xml.Element:
        r = xml.Element(self.tag)

        r.set("id", self.id)
        r.set("version", str(self.version))

        if self.comment is not None:
            r.set("comment", self.comment)

        if self.operator is not None:
            r.set("operator", self.operator.value)

        if self.deprecated is not None:
            r.set("deprecated", bool_to_xml(self.deprecated))

        if self.notes:
            r.append(self.notes.to_xml())

        if self.signature:
            r.append(self.signature.to_xml())

        return r


@dataclass
class StatesType:
    states: list[StateType]
    _tag = "states"

    def to_xml(self) -> xml.Element:
        r = xml.Element(self._tag)

        for st in self.states:
            r.append(st.to_xml())

        return r


@dataclass
class ObjectRefType:
    object_ref: ObjectIDPattern
    _tag = "object"

    def __post_init__(self):
        if not reObjectIDPattern.match(self.object_ref):
            raise ValueError(
                f"object_ref [{self.object_ref}] doesn't match with ObjectIDPattern"
            )

    def to_xml(self) -> xml.Element:
        r = xml.Element(self._tag)
        r.set("object_ref", self.object_ref)
        return r


@dataclass
class ObjectType:
    """Base OVAL Definitions::ObjectType"""

    tag: str  # XXX: should be set properly
    id: ObjectIDPattern
    version: int
    comment: Optional[str] = None
    deprecated: Optional[bool] = None
    notes: Optional[NotesType] = None
    signature: Optional[Signature] = None

    def __post_init__(self):
        self.tag = NonEmptyStringType(self.tag)
        self.version = UnsignedInteger(self.version)
        if self.comment is not None:
            self.comment = NonEmptyStringType(self.comment)

        if not reObjectIDPattern.match(self.id):
            raise ValueError(f"id [{self.id}] doesn't match with ObjectIDPattern")

    def to_xml(self) -> xml.Element:
        r = xml.Element(self.tag)

        r.set("id", self.id)
        r.set("version", str(self.version))

        if self.comment:
            r.set("comment", self.comment)

        if self.deprecated is not None:
            r.set("deprecated", bool_to_xml(self.deprecated))

        return r


@dataclass
class ObjectsType:
    objects: list[ObjectType]
    _tag = "objects"

    def to_xml(self) -> xml.Element:
        r = xml.Element(self._tag)

        for obj in self.objects:
            r.append(obj.to_xml())

        return r


@dataclass
class TestType:
    """Base OVAL Definitions::TestType"""

    tag: str  # XXX: should be set properly
    id: TestIDPattern
    version: int
    check: CheckEnumeration
    comment: str
    object: ObjectRefType
    states: Optional[list[StateRefType]] = None
    check_existence: Optional[ExistenceEnumeration] = None
    state_operator: Optional[OperatorEnumeration] = None
    deprecated: Optional[bool] = None
    notes: Optional[NotesType] = None
    signature: Optional[Signature] = None

    def __post_init__(self):
        self.tag = NonEmptyStringType(self.tag)
        self.version = UnsignedInteger(self.version)
        self.comment = NonEmptyStringType(self.comment)

        if not reTestIDPattern.match(self.id):
            raise ValueError(f"id [{self.id}] doesn't match with TestIDPattern")

        if not check_val_in_enum(self.check.value, CheckEnumeration):
            raise ValueError(f"check [{self.check}] not in CheckEnumeration")

        if self.check_existence is not None and not check_val_in_enum(
            self.check_existence.value, ExistenceEnumeration
        ):
            raise ValueError(
                f"check_existence [{self.check_existence}] not in ExistenceEnumeration"
            )

        if self.state_operator is not None and not check_val_in_enum(
            self.state_operator.value, OperatorEnumeration
        ):
            raise ValueError(
                f"state_operator [{self.state_operator}] not in OperatorEnumeration"
            )

    def to_xml(self) -> xml.Element:
        r = xml.Element(self.tag)

        r.set("id", self.id)
        r.set("version", str(self.version))
        r.set("check", self.check.value)
        r.set("comment", self.comment)

        if self.check_existence is not None:
            r.set("check_existence", self.check_existence.value)

        if self.state_operator is not None:
            r.set("state_operator", self.state_operator.value)

        if self.deprecated is not None:
            r.set("deprecated", bool_to_xml(self.deprecated))

        r.append(self.object.to_xml())

        if self.states:
            for st in self.states:
                r.append(st.to_xml())

        if self.notes:
            r.append(self.notes.to_xml())

        if self.signature:
            r.append(self.signature.to_xml())

        return r


@dataclass
class TestsType:
    tests: list[TestType]
    _tag = "tests"

    def to_xml(self) -> xml.Element:
        r = xml.Element(self._tag)

        for t in self.tests:
            r.append(t.to_xml())

        return r


@dataclass
class OvalDefinitions:
    generator: GeneratorType
    definitions: Optional[DefinitionsType] = None
    tests: Optional[TestsType] = None
    objects: Optional[ObjectsType] = None
    states: Optional[StatesType] = None
    variables: Optional[VariablesType] = None
    signature: Optional[Signature] = None
    _tag = "oval_definitions"

    def to_xml(self) -> xml.Element:
        r = xml.Element(self._tag, ns)

        r.append(self.generator.to_xml())
        if self.definitions is not None:
            r.append(self.definitions.to_xml())
        if self.tests is not None:
            r.append(self.tests.to_xml())
        if self.objects is not None:
            r.append(self.objects.to_xml())
        if self.states is not None:
            r.append(self.states.to_xml())
        if self.variables is not None:
            r.append(self.variables.to_xml())
        if self.signature is not None:
            r.append(self.signature.to_xml())

        return r
