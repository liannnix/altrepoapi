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

import inspect

from enum import Enum
from typing import Any, List, NamedTuple, Type, TypeVar, Union, get_type_hints

from .base import JSONValue, JSONObject
from .rusty import Result, Ok, Err

SKIP_SERILIZING_IF_NONE = "SKIP_SERILIZING_IF_NONE"

EN = TypeVar("EN", bound=Enum)


class SerdeError(Exception):
    pass


def serialize_enum(cls: Enum) -> str:
    return cls.value


def deserialize_enum(cls: Type[EN], value: JSONValue) -> Result[EN, SerdeError]:
    if not isinstance(value, str):
        return Err(SerdeError(f"Expected string, got {type(value)}"))
    v = value.upper()
    try:
        return Ok(cls[v])  # type: ignore
    except KeyError:
        return Err(
            SerdeError(f"'{v}'[{value}] is not a valid {cls.__name__} enum member")
        )


def _is_enum_type(obj: Type) -> bool:
    """Check if an object is an Enum class (not an instance)"""
    return isinstance(obj, type) and issubclass(obj, Enum)


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
    """Check if an object is a NamedTuple instance  with type annotations"""
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


def _maybe_deserialize(obj: Type, value) -> Result[Any, SerdeError]:
    """Deserialize Enum if it implements `deserialize` method or primitive type value."""
    if _is_enum_type(obj):
        if deserialize := getattr(obj, "deserialize"):
            return deserialize(value)
    return Ok(value)


T = TypeVar("T", bound=NamedTuple)


def deserialize(cls: Type[T], data: JSONObject) -> Result[T, SerdeError]:
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
                            f"Expected dict in list for {field}, got {type(item)}"
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
                                        f"Expected dict in list for {field}, got {type(item)}"
                                    )
                                )
                            d = deserialize(namedtuple_cls, item)
                            if d.is_err():
                                return d
                            deserialized_list.append(d.unwrap())
                        kwargs[field] = deserialized_list
                        break
            else:
                # handle optional Enum or regular value
                v = _maybe_deserialize(field_type, value)
                if v.is_err():
                    return v
                kwargs[field] = v.unwrap()
        # handle enum types that implements 'deserialize' method and primitive types
        else:
            v = _maybe_deserialize(field_type, value)
            if v.is_err():
                return v
            kwargs[field] = v.unwrap()

    return Ok(cls(**kwargs))  # type: ignore


def serialize(cls: NamedTuple, skip_nones: bool = False) -> JSONObject:
    json: dict[str, JSONValue] = {}

    # use class var if not forced to skip None value fields from serialization
    if not skip_nones and hasattr(cls, SKIP_SERILIZING_IF_NONE):
        skip_nones = cls.SKIP_SERILIZING_IF_NONE  # type: ignore

    for key, value in cls._asdict().items():  # type: ignore
        if isinstance(value, list):
            # handle list of serializable values
            serialized_list = []
            for item in value:
                serialized_list.append(serialize(item))
            v = serialized_list
        elif _is_namedtuple_instance(value):
            # handle nested objects serialization recursively
            v = serialize(value, skip_nones)
        elif hasattr(value, "serialize"):
            # handle objects that has specific serialization method
            v = value.serialize()
        else:
            v = value
        # skip fields with None value if specified
        if skip_nones and v is None:
            continue
        json[key] = v

    return json
