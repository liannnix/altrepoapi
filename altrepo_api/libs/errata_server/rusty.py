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

from collections import deque
from functools import reduce, wraps
from itertools import islice, takewhile, dropwhile, chain
from typing import (
    Any,
    Callable,
    Generic,
    Iterable,
    Iterator,
    NamedTuple,
    NoReturn,
    Optional,
    TypeVar,
    Union,
    overload,
)

T = TypeVar("T")  # Contained value type
E = TypeVar("E")  # Error value type
U = TypeVar("U")  # Mapping return type
F = TypeVar("F")  # New error type


class Ok(NamedTuple, Generic[T]):
    """
    A Rust-like Reuslt type that represents Ok(T) value.
    """

    value: T

    def __bool__(self) -> bool:
        return True

    def __repr__(self) -> str:
        return f"Ok({self.value})"

    def op_and(self, res: "Result[U, E]") -> "Result[U, E]":
        return res

    def op_or(self, res: "Result[T, F]") -> "Result[T, F]":
        return self

    def ok(self) -> "Option[T]":
        return Option.some(self.value)

    def err(self) -> "Option[object]":
        return Option.none()

    def inspect(self, op: Callable[[T], Any]) -> "Ok[T]":
        op(self.value)
        return self

    def inspect_err(self, _op: Callable[[E], Any]) -> "Ok[T]":
        return self

    def iter(self) -> "Iter[T]":
        return Iter((self.value,))

    def is_ok(self) -> bool:
        return True

    def is_err(self) -> bool:
        return False

    def expect(self, _msg: str) -> T:
        return self.value

    def unwrap(self) -> T:
        return self.value

    def unwrap_or(self, _default: T) -> T:
        return self.value

    def unwrap_or_else(self, _op: Callable[[Any], U]) -> T:
        return self.value

    def map(self, op: Callable[[T], U]) -> "Ok[U]":
        return Ok(op(self.value))

    def map_err(self, _op: Callable[[Any], Any]) -> "Result[T, E]":
        return self

    def map_or(self, _default: U, op: Callable[[T], U]) -> U:
        return op(self.value)

    def map_or_else(self, _default: Callable[[], U], op: Callable[[T], U]) -> U:
        return op(self.value)

    def and_then(self, op: Callable[[T], "Result[U, E]"]) -> "Result[U, E]":
        return op(self.value)

    def or_else(self, _op: Callable[[], "Result[U, E]"]) -> "Result[T, E]":
        return self


class Err(NamedTuple, Generic[E]):
    """
    A Rust-like Reuslt type that represents Err(E) value.
    """

    error: E

    def __bool__(self) -> bool:
        return False

    def __repr__(self) -> str:
        return f"Err({self.error})"

    def op_and(self, _res: "Result[U, E]") -> "Result[U, E]":
        return self

    def op_or(self, res: "Result[T, F]") -> "Result[T, F]":
        return res

    def ok(self) -> "Option[object]":
        return Option.none()

    def err(self) -> "Option[E]":
        return Option.some(self.error)

    def inspect(self, _op: Callable[[T], Any]) -> "Err[E]":
        return self

    def inspect_err(self, op: Callable[[E], Any]) -> "Err[E]":
        op(self.error)
        return self

    def iter(self) -> "Iter[object]":
        return Iter(tuple())

    def is_ok(self) -> bool:
        return False

    def is_err(self) -> bool:
        return True

    def expect(self, msg: str) -> NoReturn:
        raise RuntimeError(msg)

    def unwrap(self) -> NoReturn:
        if isinstance(self.error, Exception):
            raise self.error
        return self.expect(f"Called unwrap() on Err: {self.error}")

    def unwrap_or(self, default: U) -> U:
        return default

    def unwrap_or_else(self, op: Callable[[E], U]) -> U:
        return op(self.error)

    def map(self, _op: Callable[[Any], Any]) -> "Result[U, E]":
        return self

    def map_err(self, op: Callable[[E], F]) -> "Err[F]":
        return Err(op(self.error))

    def map_or(self, default: U, _op: Callable[[T], U]) -> U:
        return default

    def map_or_else(self, default: Callable[[], U], _op: Callable[[T], U]) -> U:
        return default()

    def and_then(self, _op: Callable[[Any], "Result[U, E]"]) -> "Result[U, E]":
        return self

    def or_else(self, op: Callable[[], "Result[U, E]"]) -> "Result[U, E]":
        return op()


Result = Union[Ok[T], Err[E]]


def resultify(f: Callable[..., T]) -> Callable[..., Result[T, Exception]]:
    """Decorator to wrap function that may raise an exception into a Result value."""

    @wraps(f)
    def wrapper(*args: Any, **kwargs: Any) -> Result[T, Exception]:
        try:
            return Ok(f(*args, **kwargs))
        except Exception as e:
            return Err(e)

    return wrapper


def resultify_method(f: Callable[..., T]) -> Callable[..., Result[T, Exception]]:
    """Decorator to wrap class' method that may raise an exception into a Resul value."""

    @wraps(f)
    def wrapper(self, *args: Any, **kwargs: Any) -> Result[T, Exception]:
        try:
            return Ok(f(self, *args, **kwargs))
        except Exception as e:
            return Err(e)

    return wrapper


class Option(NamedTuple, Generic[T]):
    """
    A Rust-like Option type that represents either Some(value) or None.
    """

    value: Optional[T] = None

    @classmethod
    def some(cls, value: T) -> "Option[T]":
        if value is None:
            raise ValueError("Some cannot contain None. Use Option.none() instead.")
        return cls(value)

    @classmethod
    def none(cls) -> "Option[T]":
        return cls()

    def is_some(self) -> bool:
        return self.value is not None

    def is_none(self) -> bool:
        return self.value is None

    def op_and(self, opt: "Option[U]") -> "Option[U]":
        return opt if self.is_some() else Option.none()

    def op_or(self, opt: "Option[T]") -> "Option[T]":
        return self if self.is_some() else opt

    def expect(self, msg: str) -> T:
        if self.value is None:
            raise ValueError(msg)
        return self.value

    def inspect(self, op: Callable[[T], Any]) -> "Option[T]":
        if self.value is not None:
            op(self.value)
        return self

    def iter(self) -> "Iter[T]":
        return Iter((self.value,)) if self.value is not None else Iter(())

    def unwrap(self) -> T:
        return self.expect("Called unwrap() on a None value")

    def unwrap_or(self, default: T) -> T:
        return self.value if self.value is not None else default

    def unwrap_or_else(self, f: Callable[[], T]) -> T:
        return self.value if self.value is not None else f()

    def map(self, f: Callable[[T], U]) -> "Option[U]":
        return Option.some(f(self.value)) if self.value is not None else Option.none()

    def map_or(self, default: U, f: Callable[[T], U]) -> U:
        return f(self.value) if self.value is not None else default

    def map_or_else(self, default: Callable[[], U], f: Callable[[T], U]) -> U:
        return f(self.value) if self.value is not None else default()

    def and_then(self, f: Callable[[T], "Option[U]"]) -> "Option[U]":
        return f(self.value) if self.value is not None else Option.none()

    def or_else(self, f: Callable[[], "Option[T]"]) -> "Option[T]":
        return self if self.is_some() else f()

    def filter(self, predicate: Callable[[T], bool]) -> "Option[T]":
        return (
            self
            if (self.value is not None and predicate(self.value))
            else Option.none()
        )

    def ok_or(self, err: E) -> "Result[T, E]":
        return Ok(self.value) if self.value is not None else Err(err)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Option):
            return False
        return self.value == other.value

    def __repr__(self) -> str:
        return f"Some({self.value})" if self.is_some() else "None"

    def __bool__(self) -> bool:
        return self.is_some()


def optionable(func: Callable[..., Optional[T]]) -> Callable[..., Option[T]]:
    """Decorator to wrap function that may return None into an Option value."""

    @wraps(func)
    def wrapper(*args, **kwargs) -> Option[T]:
        return Option(func(*args, **kwargs))

    return wrapper


def optionable_method(func: Callable[..., Optional[T]]) -> Callable[..., Option[T]]:
    """Decorator to wrap class' method that may return None into an Option value."""

    @wraps(func)
    def wrapper(self, *args, **kwargs) -> Option[T]:
        return Option(func(self, *args, **kwargs))

    return wrapper


def _sliding_window(iterable: Iterable[T], size: int) -> Iterator[tuple[T, ...]]:
    """
    Yield sliding windows of width 'size' over the iterable.
    Similar to Rust's slice::windows() method.
    """
    if size <= 0:
        raise ValueError("Window size must be positive")

    it = iter(iterable)
    window = deque(islice(it, size), maxlen=size)

    if len(window) < size:
        return  # Not enough elements for even one window

    yield tuple(window)

    for item in it:
        window.append(item)
        yield tuple(window)


class Iter(Generic[T]):
    """
    A Rust-inspired iterator that provides chainable operations on any iterable.
    All operations are lazy (evaluated only when consumed).
    """

    __slots__ = ("_iterable",)

    def __init__(self, iterable: Iterable[T]):
        self._iterable = iter(iterable)

    def __iter__(self) -> Iterator[T]:
        return self._iterable

    def collect(self) -> list[T]:
        return list(self._iterable)

    def collect_tuple(self) -> tuple[T, ...]:
        return tuple(self._iterable)

    def collect_set(self) -> set[T]:
        return set(self._iterable)

    def map(self, f: Callable[[T], U]) -> "Iter[U]":
        return Iter(f(x) for x in self._iterable)

    def next(self) -> Option[T]:
        return Option(next(self._iterable, None))

    def filter(self, predicate: Callable[[T], bool]) -> "Iter[T]":
        return Iter(x for x in self._iterable if predicate(x))

    def filter_map(self, f: Callable[[T], Option[U]]) -> "Iter[U]":
        return Iter(y.unwrap() for x in self._iterable if (y := f(x)).is_some())

    # TODO: deal with the type inference for `flat_map` and `flatten` methods
    #
    # For single level depth iterables with simple types it is better use `flat_map`
    # method:
    #   > x = Iter([[1, 2], [3, 4]]).flat_map(lambda x: x).collect() => list[int]
    #
    # For single level depth iterables that contains `Result` or `Option` type values
    # it is better use `flatten` method:
    #   > x = Iter([Ok(123), Ok(321), Err(None)]).flatten().collect() => list[int]
    #
    # For deeper level nested iterables use `flat_map` in chain with `flat_map` or
    # `flatten` in accordance to underlying contents.

    @staticmethod
    def _into_iter(v: Union[Iterable[U], Result[U, E], Option[U], T]) -> Iterable[U]:
        """
        Handles Rust-like implementation of `IntoIter` trait for `Result[T,E]`
        and `Option[T]` types.
        """

        if isinstance(v, (Ok, Err, Option)):
            return v.iter()  # type: ignore
        if isinstance(v, Iterable):
            return v
        raise ValueError("Type %s is not iterable" % type(v))

    def flat_map(self, f: Callable[[T], Iterable[U]]) -> "Iter[U]":
        return Iter(y for x in self._iterable for y in self._into_iter(f(x)))

    @overload
    def flatten(self: "Iter[Iterable[U]]") -> "Iter[U]": ...

    @overload
    def flatten(self: "Iter[Result[U, E]]") -> "Iter[U]": ...

    @overload
    def flatten(self: "Iter[Option[U]]") -> "Iter[U]": ...

    @overload
    def flatten(self: "Iter[Any]") -> Any: ...

    def flatten(self):
        return Iter(y for x in self._iterable for y in self._into_iter(x))

    def take(self, n: int) -> "Iter[T]":
        return Iter(islice(self._iterable, n))

    def take_while(self, predicate: Callable[[T], bool]) -> "Iter[T]":
        return Iter(takewhile(predicate, self._iterable))

    def skip(self, n: int) -> "Iter[T]":
        return Iter(islice(self._iterable, n, None))

    def skip_while(self, predicate: Callable[[T], bool]) -> "Iter[T]":
        return Iter(dropwhile(predicate, self._iterable))

    def chain(self, other: Iterable[T]) -> "Iter[T]":
        return Iter(chain(self._iterable, other))

    def zip(self, other: Iterable[U]) -> "Iter[tuple[T, U]]":
        return Iter(zip(self._iterable, other))

    def enumerate(self) -> "Iter[tuple[int, T]]":
        return Iter(enumerate(self._iterable))

    def inspect(self, f: Callable[[T], Any]) -> "Iter[T]":
        return Iter(self._inspect_generator(f))

    def _inspect_generator(self, f: Callable[[T], Any]) -> Iterator[T]:
        for x in self._iterable:
            f(x)
            yield x

    def fold(self, init: U, f: Callable[[U, T], U]) -> U:
        return reduce(f, self._iterable, init)

    def reduce(self, f: Callable[[T, T], T]) -> Option[T]:
        try:
            return Option.some(reduce(f, self._iterable))
        except TypeError:
            return Option.none()

    def all(self, predicate: Callable[[T], bool]) -> bool:
        return all(predicate(x) for x in self._iterable)

    def any(self, predicate: Callable[[T], bool]) -> bool:
        return any(predicate(x) for x in self._iterable)

    def find(self, predicate: Callable[[T], bool]) -> Option[T]:
        return Option(next((x for x in self._iterable if predicate(x)), None))

    def position(self, predicate: Callable[[T], bool]) -> Option[int]:
        return Option(
            next((i for i, x in enumerate(self._iterable) if predicate(x)), None)
        )

    def rposition(self, predicate: Callable[[T], bool]) -> Option[int]:
        items = list(self._iterable)
        return Option(
            next(
                (
                    len(items) - 1 - i
                    for i, x in enumerate(reversed(items))
                    if predicate(x)
                ),
                None,
            )
        )

    def count(self) -> int:
        return sum(1 for _ in self._iterable)

    def last(self) -> Option[T]:
        last_item = None
        for last_item in self._iterable:
            pass
        return Option(last_item)

    def nth(self, n: int) -> Option[T]:
        return Option(next(islice(self._iterable, n, None), None))

    def windows(self, size: int) -> "Iter[tuple[T, ...]]":
        return Iter(_sliding_window(self._iterable, size))

    def partition(self, predicate: Callable[[T], bool]) -> tuple[list[T], list[T]]:
        a, b = [], []
        for x in self._iterable:
            (a if predicate(x) else b).append(x)
        return (a, b)

    def for_each(self, f: Callable[[T], Any]):
        for x in self._iterable:
            f(x)


def into_iter(v: Iterable[T]) -> Iter[T]:
    """Wraps iterable into an Iter class instance."""
    return Iter(v)
