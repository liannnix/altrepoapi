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

from functools import wraps
from typing import Generic, TypeVar, Union, NoReturn, Callable, Any, NamedTuple

T = TypeVar("T")  # Success value type
E = TypeVar("E")  # Error value type
U = TypeVar("U")  # Mapping return type
F = TypeVar("F")  # New error type for map_err


class Ok(NamedTuple, Generic[T]):
    value: T

    def __repr__(self) -> str:
        return f"Ok({self.value})"

    def is_ok(self) -> bool:
        return True

    def is_err(self) -> bool:
        return False

    def unwrap(self) -> T:
        return self.value

    def unwrap_or(self, _default: T) -> T:
        return self.value

    def unwrap_or_else(self, op: Callable[[Any], U]) -> T:
        return self.value

    def map(self, op: Callable[[T], U]) -> "Ok[U]":
        return Ok(op(self.value))

    def map_err(self, _op: Callable[[Any], Any]) -> "Result[T, E]":
        return self

    def and_then(self, op: Callable[[T], "Result[U, E]"]) -> "Result[U, E]":
        return op(self.value)


class Err(NamedTuple, Generic[E]):
    error: E

    def __repr__(self) -> str:
        return f"Err({self.error})"

    def is_ok(self) -> bool:
        return False

    def is_err(self) -> bool:
        return True

    def unwrap(self) -> NoReturn:
        raise RuntimeError(f"Called unwrap() on Err: {self.error}")

    def unwrap_or(self, default: U) -> U:
        return default

    def unwrap_or_else(self, op: Callable[[E], U]) -> U:
        return op(self.error)

    def map(self, _op: Callable[[Any], Any]) -> "Result[U, E]":
        return self

    def map_err(self, op: Callable[[E], F]) -> "Err[F]":
        return Err(op(self.error))

    def and_then(self, _op: Callable[[Any], "Result[U, E]"]) -> "Result[U, E]":
        return self


Result = Union[Ok[T], Err[E]]


def resultify(f: Callable[..., T]) -> Callable[..., Result[T, Exception]]:
    """Decorator to convert exceptions to Err results"""

    @wraps(f)
    def wrapper(*args: Any, **kwargs: Any) -> Result[T, Exception]:
        try:
            return Ok(f(*args, **kwargs))
        except Exception as e:
            return Err(e)

    return wrapper
