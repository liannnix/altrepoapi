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

import datetime
from typing import Any


def generate_sort_key_tuple(
    obj: dict[str, Any], ordering: tuple[str, ...]
) -> tuple[int, ...]:
    """
    Generates sorting key to use with standard `sorted()` function call as lambda.
    :param obj: element of iterable to be sorted
    :param ordering: list of object's attribute names optionally
                     preceded with '-' to reverse sorting order
    :return: tuple: tuple of integers to be used for sorting
                    by lambda in `sorted()` call.
    """

    def string_chars_to_ints(s: str) -> tuple[int, ...]:
        if not s:
            return (0,)

        return tuple([ord(x.lower()) for x in s])

    sort_key = []

    for field in ordering:
        # handle ordering key sign that indicates reverse ordering
        if field.startswith("-"):
            attr_name = field.lstrip("-")
            sign = -1
        else:
            attr_name = field
            sign = 1
        # get value by attribute name
        val = obj.get(attr_name, None)
        # generate integer representation of attribute's value
        # and append to sort_key tuple
        if isinstance(val, int) or isinstance(val, float):
            int_repr = int(val)
        elif isinstance(val, bool):
            int_repr = int(val)
        elif isinstance(val, datetime.datetime):
            int_repr = int(val.timestamp())
        elif isinstance(val, datetime.date):
            val = datetime.datetime.strptime(str(val), "%Y-%m-%d")
            int_repr = int(val.timestamp())
        elif isinstance(val, str):
            int_repr = string_chars_to_ints(val)
        else:
            int_repr = 0
        # handle sorting order
        if isinstance(int_repr, tuple):
            sort_key.append(tuple([sign * x for x in int_repr]))
        else:
            sort_key.append(sign * int_repr)

    return tuple(sort_key) if sort_key else (0,)


def rich_sort(
    object_list: list[dict[str, Any]], ordering: list[str]
) -> list[dict[str, Any]]:
    """
    Sorting a list of dictionaries by several keys.
    :param object_list: element of iterable to be sorted
    :param ordering: list of object's attribute names optionally
                     preceded with '-' to reverse sorting order
    """

    try:
        return sorted(
            object_list,
            key=lambda k: generate_sort_key_tuple(k, tuple(ordering)),
        )
    except AttributeError:
        return object_list
