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

import xml.etree.ElementTree as xml

from dataclasses import dataclass
from typing import Literal, Optional, Union

from .oval_definitions.type import (
    Filter,
    NotesType,
    ObjectType,
    ObjectRefType,
    Signature,
    StateType,
    StateRefType,
    TestType,
)
from .oval_definitions.entity import (
    EntityObjectIntType,
    EntityObjectStringType,
    EntityStateIntType,
    EntityStateStringType,
    EntityStateAnySimpleType,
)
from .oval_definitions.enumeration import (
    CheckEnumeration,
    ExistenceEnumeration,
    OperatorEnumeration,
)
from .oval_definitions.utils import bool_to_xml


@dataclass
class FileBehaviors:
    max_depth: Optional[int] = None
    recurse: Union[
        Literal["directories", "symlinks", "symlinks and directories"], None
    ] = None
    recurse_direction: Union[Literal["none", "up", "down"], None] = None
    recurse_file_system: Union[Literal["all", "local", "defined"], None] = None
    windows_view: Union[Literal["32_bit", "64_bit"], None] = None
    _tag = "behaviors"

    def to_xml(self) -> xml.Element:
        r = xml.Element(self._tag)
        if self.max_depth is not None:
            r.set("max_depth", str(self.max_depth))
        if self.recurse is not None:
            r.set("recurse", self.recurse)
        if self.recurse_direction is not None:
            r.set("recurse_direction", self.recurse_direction)
        if self.recurse_file_system is not None:
            r.set("recurse_file_system", self.recurse_file_system)
        if self.windows_view is not None:
            r.set("windows_view", self.windows_view)
        return r


# textfilecontent54 classes
@dataclass
class Textfilecontent54Behaviors(FileBehaviors):
    ignore_case: Optional[bool] = None
    multiline: Optional[bool] = None
    singleline: Optional[bool] = None

    def to_xml(self) -> xml.Element:
        r = super().to_xml()
        if self.ignore_case is not None:
            r.set("ignore_case", bool_to_xml(self.ignore_case))
        if self.multiline is not None:
            r.set("multiline", bool_to_xml(self.multiline))
        if self.singleline is not None:
            r.set("singleline", bool_to_xml(self.singleline))
        return r


@dataclass
class Textfilecontent54Test(TestType):
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
            "textfilecontent54_test",
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


@dataclass
class Textfilecontent54Object(ObjectType):
    filepath: EntityObjectStringType = None  # type: ignore
    path: EntityObjectStringType = None  # type: ignore
    filename: EntityObjectStringType = None  # type: ignore
    pattern: EntityObjectStringType = None  # type: ignore
    instance: EntityObjectIntType = None  # type: ignore
    behaviors: Optional[Textfilecontent54Behaviors] = None
    filters: Optional[list[Filter]] = None

    def __init__(
        self,
        *,
        id: str,
        version: int,
        filepath: Union[EntityObjectStringType, None],
        path: Union[EntityObjectStringType, None],
        filename: Union[EntityObjectStringType, None],
        pattern: EntityObjectStringType,
        instance: EntityObjectIntType,
        behaviors: Optional[Textfilecontent54Behaviors] = None,
        filters: Optional[list[Filter]] = None,
        comment: Optional[str] = None,
        deprecated: Optional[bool] = None,
        notes: Optional[NotesType] = None,
        signature: Optional[Signature] = None,
    ):
        if filepath is not None and (path is not None or filename is not None):
            raise ValueError(
                "Either `filepath` or `path` and `filename` should be specified"
            )
        if (path is not None and filename is None) or (
            path is None and filename is not None
        ):
            raise ValueError("Both `path` and `filename` should be specified")
        self.filepath = filepath  # type: ignore
        self.path = path  # type: ignore
        self.filename = filename  # type: ignore
        self.pattern = pattern
        self.instance = instance
        self.behaviors = behaviors
        self.filters = filters
        super().__init__(
            "textfilecontent54_object",
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

        if self.filepath is not None:
            r.append(self.filepath.to_xml())
        if self.path is not None:
            r.append(self.path.to_xml())
        if self.filename is not None:
            r.append(self.filename.to_xml())
        r.append(self.pattern.to_xml())
        r.append(self.instance.to_xml())

        if self.filters:
            for fl in self.filters:
                r.append(fl.to_xml())

        return r


@dataclass
class Textfilecontent54State(StateType):
    filepath: Optional[EntityStateStringType] = None
    path: Optional[EntityStateStringType] = None
    filename: Optional[EntityStateStringType] = None
    pattern: Optional[EntityStateStringType] = None
    instance: Optional[EntityStateIntType] = None
    text: Optional[EntityStateAnySimpleType] = None
    subexpression: Optional[EntityStateAnySimpleType] = None
    # not implemented
    windows_view = None

    def __init__(
        self,
        *,
        id: str,
        version: int,
        filepath: Optional[EntityStateStringType] = None,
        path: Optional[EntityStateStringType] = None,
        filename: Optional[EntityStateStringType] = None,
        pattern: Optional[EntityStateStringType] = None,
        instance: Optional[EntityStateIntType] = None,
        text: Optional[EntityStateAnySimpleType] = None,
        subexpression: Optional[EntityStateAnySimpleType] = None,
        windows_view=None,
        comment: Optional[str] = None,
        operator: Optional[OperatorEnumeration] = None,
        deprecated: Optional[bool] = None,
        notes: Optional[NotesType] = None,
        signature: Optional[Signature] = None,
    ):
        self.filepath = filepath
        self.path = path
        self.filename = filename
        self.pattern = pattern
        self.instance = instance
        self.text = text
        self.subexpression = subexpression
        self.windows_view = windows_view
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

        if self.filepath is not None:
            r.append(self.filepath.to_xml())
        if self.path is not None:
            r.append(self.path.to_xml())
        if self.filename is not None:
            r.append(self.filename.to_xml())
        if self.pattern is not None:
            r.append(self.pattern.to_xml())
        if self.instance is not None:
            r.append(self.instance.to_xml())
        if self.text is not None:
            r.append(self.text.to_xml())
        if self.subexpression is not None:
            r.append(self.subexpression.to_xml())
        # if self.windows_view is not None:
        #     r.append(self.windows_view.to_xml())

        return r
