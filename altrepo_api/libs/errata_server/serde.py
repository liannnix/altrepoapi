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

"""
A lightweight, type-safe JSON (de)serializer for NamedTuple-based models.

Features:
- Automatic handling of datetime, UUID, Enum, nested NamedTuples, and lists
- Optional field support (Union[T, None])
- Custom enum deserialization via `.deserialize()` classmethod
- Strict boolean handling (only native JSON booleans accepted)
- Configurable None-skipping during serialization
"""

import inspect

from enum import Enum
from datetime import datetime
from typing import Any, Callable, List, NamedTuple, Type, TypeVar, Union, get_type_hints
from uuid import UUID

from .base import JSONValue, JSONObject
from .rusty import Result, Ok, Err, resultify

SKIP_SERIALIZING_IF_NONE = "SKIP_SERIALIZING_IF_NONE"

ENUM = TypeVar("ENUM", bound=Enum)


class SerdeError(Exception):
    pass


def serialize_enum(cls: Enum) -> str:
    """Simple Enum serializer."""
    return str(cls.value).lower()


def deserialize_enum(cls: Type[ENUM], value: JSONValue) -> Result[ENUM, Exception]:
    """
    Deserialize a string into an Enum member.

    Tries in order:
    1. Enum member name (case-insensitive)
    2. Enum value (converted to string, then case-insensitive match)

    Returns Err if no match is found.
    """

    if not isinstance(value, str):
        return Err(SerdeError(f"Invalid value {type(value).__name__}. Expected string"))

    v = value.upper()

    try:
        return Ok(cls[v])
    except KeyError:
        pass

    for member in cls:
        if str(member.value).upper() == v:
            return Ok(member)

    return Err(SerdeError(f"'{value}' is not a valid {cls.__name__}"))


def _is_namedtuple_type(obj_type: Type) -> bool:
    """Check if a class is a NamedTuple with type annotations"""
    return (
        inspect.isclass(obj_type)
        and issubclass(obj_type, tuple)
        and hasattr(obj_type, "_fields")
        and hasattr(obj_type, "_asdict")
        and hasattr(obj_type, "__annotations__")
    )


def _is_namedtuple_instance(obj) -> bool:
    """Check if an object is a NamedTuple instance with type annotations"""
    if not isinstance(obj, tuple):
        return False
    return (
        hasattr(obj.__class__, "_fields")
        and hasattr(obj.__class__, "_asdict")
        and hasattr(obj.__class__, "__annotations__")
        and isinstance(obj.__class__.__annotations__, dict)
    )


def _get_underlying_namedtuple(type_hint):
    """Extract NamedTuple from List[NamedTuple] or Optional[List[NamedTuple]]"""
    if hasattr(type_hint, "__origin__"):
        if type_hint.__origin__ is list or type_hint.__origin__ is List:
            args = type_hint.__args__
            if len(args) == 1 and _is_namedtuple_type(args[0]):
                return args[0]
        elif type_hint.__origin__ is Union:
            for arg in type_hint.__args__:
                if result := _get_underlying_namedtuple(arg):
                    return result
    return None


def _try_deserialize_enum(obj: Type, value) -> Result[Enum, Exception]:
    # deserialize Enum if it implements `deserialize` static or class method
    if hasattr(obj, "deserialize"):
        deserialize: Callable[..., Enum] = obj.deserialize
        try:
            return Ok(deserialize(value))
        except Exception as e:
            return Err(e)
    return deserialize_enum(obj, value)


@resultify
def _try_deserialize_datetime(value):
    return datetime.fromisoformat(value)


@resultify
def _try_deserialize_uuid(value):
    return UUID(value)


@resultify
def _try_deserialize_int(value):
    return int(value)


@resultify
def _try_deserialize_float(value):
    return float(value)


def _try_deserialize(obj: Type, value) -> Result[Any, Exception]:
    if isinstance(obj, type):
        # deserialize Enum
        if issubclass(obj, Enum):
            return _try_deserialize_enum(obj, value)
        # deserialize datetime
        if issubclass(obj, datetime):
            return _try_deserialize_datetime(value)
        # deserialize UUID
        if issubclass(obj, UUID):
            return _try_deserialize_uuid(value)
        # deserialize bool
        # Note: supports only native JSON boolean type
        if issubclass(obj, bool):
            return Ok(value)
        # deserialize int
        if issubclass(obj, int):
            return _try_deserialize_int(value)
        # deserialize float
        if issubclass(obj, float):
            return _try_deserialize_float(value)
    # fallback to default
    return Ok(value)


T = TypeVar("T", bound=NamedTuple)


def deserialize(cls: Type[T], data: JSONObject) -> Result[T, Exception]:
    if not _is_namedtuple_type(cls):
        return Err(SerdeError(f"{cls.__name__} is not a NamedTuple class"))

    field_types = get_type_hints(cls)
    kwargs = {}

    for field, field_type in field_types.items():
        if field not in data:
            if field in cls._field_defaults:
                continue  # use default value
            return Err(SerdeError(f"Missing required field: {field}"))

        value = data[field]

        # handle list[NamedTuple]
        if namedtuple_cls := _get_underlying_namedtuple(field_type):
            if not isinstance(value, list):
                return Err(SerdeError(f"Expected list for {field}, got {type(value)}"))

            deserialized_list = []
            for item in value:
                if not isinstance(item, dict):
                    return Err(
                        SerdeError(
                            f"Expected dict for field '{field}', got {type(value).__name__}"
                        )
                    )
                d = deserialize(namedtuple_cls, item)
                if d.is_err():
                    return d
                deserialized_list.append(d.unwrap())
            kwargs[field] = deserialized_list
        # handle nested NamedTuples
        elif _is_namedtuple_type(field_type):
            if not isinstance(value, dict):
                return Err(SerdeError(f"Expected dict for {field}, got {type(value)}"))
            d = deserialize(field_type, value)
            if d.is_err():
                return d
            kwargs[field] = d.unwrap()
        # handle Optional[Something] cases
        elif hasattr(field_type, "__origin__") and field_type.__origin__ is Union:
            for arg in field_type.__args__:
                # handle Optional[NamedTuple] case
                if _is_namedtuple_type(arg):
                    if isinstance(value, dict):
                        d = deserialize(arg, value)
                        if d.is_err():
                            return d
                        kwargs[field] = d.unwrap()
                        break
                # handle Optional[List[NamedTuple]] case
                elif namedtuple_cls := _get_underlying_namedtuple(arg):
                    if isinstance(value, list):
                        deserialized_list = []
                        for item in value:
                            if not isinstance(item, dict):
                                return Err(
                                    SerdeError(
                                        f"Expected dict in list for '{field}', got {type(item).__name__}"
                                    )
                                )
                            d = deserialize(namedtuple_cls, item)
                            if d.is_err():
                                return d
                            deserialized_list.append(d.unwrap())
                        kwargs[field] = deserialized_list
                        break
                elif value is not None:
                    # handle optional Enum or regular value
                    v = _try_deserialize(arg, value)
                    if v.is_err():
                        return v
                    kwargs[field] = v.unwrap()
                    break
                elif value is None and type(None) in field_type.__args__:
                    # handle optional field without default value
                    kwargs[field] = None
                    break
                else:
                    return Err(SerdeError(f"Unexpected None value for field '{field}'"))
        # handle enum types that implements 'deserialize' method and primitive types
        else:
            v = _try_deserialize(field_type, value)
            if v.is_err():
                return v
            kwargs[field] = v.unwrap()

    return Ok(cls(**kwargs))  # type: ignore


def _serialize(value: Any) -> JSONValue:
    # handle objects that has specific serialization method
    if hasattr(value, "serialize"):
        return value.serialize()
    # handle datetime
    if isinstance(value, datetime):
        return value.isoformat()
    # handle uuid
    if isinstance(value, UUID):
        return str(value)
    # fallback to default
    return value


def serialize(cls: NamedTuple, skip_nones: bool = False) -> JSONObject:
    json: dict[str, JSONValue] = {}

    # use class var if not forced to skip None value fields from serialization
    if not skip_nones and hasattr(cls, SKIP_SERIALIZING_IF_NONE):
        skip_nones = cls.SKIP_SERIALIZING_IF_NONE  # type: ignore

    for key, value in cls._asdict().items():  # type: ignore
        if isinstance(value, list):
            # handle list of serializable values
            serialized_list = []

            for item in value:
                if _is_namedtuple_instance(item):
                    serialized_list.append(serialize(item, skip_nones))
                else:
                    serialized_list.append(_serialize(item))

            v = serialized_list
        elif _is_namedtuple_instance(value):
            # handle nested objects serialization recursively
            v = serialize(value, skip_nones)
        else:
            v = _serialize(value)
        # skip fields with None value if specified
        if skip_nones and v is None:
            continue
        json[key] = v

    return json
