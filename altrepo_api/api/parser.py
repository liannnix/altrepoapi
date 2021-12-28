# ALTRepo API
# Copyright (C) 2021  BaseALT Ltd

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

import re
import datetime
from flask_restx import reqparse
from typing import Any

from altrepo_api.api.misc import lut


class ParserFactory:
    """Register reqparse arguments and builds request parsers by list of items."""

    def __init__(self) -> None:
        self.items: list = []
        self.lindex: int = 0

    def register_item(self, item_name: str, **kwargs) -> int:
        """Store request parser item and return it index."""

        self.items.append((item_name, kwargs))
        self.lindex = len(self.items) - 1
        return self.lindex

    def build_parser(self, *items: int) -> reqparse.RequestParser:
        """Build RequestParser instance from list of parser's items."""

        parser = reqparse.RequestParser()
        for item in items:
            if item < 0 or item > self.lindex:
                raise IndexError("Item index out of list")
            name, kwargs = self.items[item]
            parser.add_argument(name, **kwargs)
        return parser


parser = ParserFactory()

# lookup tables
# __pkg_groups = set(lut.pkg_groups)
__known_archs = set(lut.known_archs)
__known_branches = set(lut.known_branches)


# regex patterns
__pkg_cs_match = re.compile("^[a-fA-F0-9]+$")
__pkg_name_match = re.compile("^[\w\.\+\-]{2,}$")  # type: ignore
__pkg_VR_match = re.compile("^[\w\.]+$")  # type: ignore
__pkg_groups_match = re.compile("^[A-Z][a-zA-Z0-9\+\ \/-]+$")  # type: ignore
__pkg_disttag_match = re.compile("^[a-z0-9\+\.]+$")  # type: ignore
__packager_name_match = re.compile("^[a-zA-Z]+[\w\.\ \-\@]*$")  # type: ignore
__packager_email_match = re.compile("^[\w\.\-]+@[\w\.\-]+$")  # type: ignore
__packager_nickname_match = re.compile("^[\w\-]{2,}$")  # type: ignore
# file name match allows '*' wildcard symbol
__file_name_wc_match = re.compile("^[\w\-. \*]{2,}$")  # type: ignore
__dp_name_match = re.compile("^[\w\/\(\)\.\:\-]{2,}$")  # type: ignore

# custom validators
def __get_string(value: Any) -> str:
    try:
        return str(value)
    except (TypeError, ValueError):
        raise ValueError("{0} is not a valid string".format(value))


def pkg_name_type(value: Any) -> str:
    """Package name validator."""

    value = __get_string(value)
    if not __pkg_name_match.search(value):
        raise ValueError("Invalid package name: {0}".format(value))
    return value

pkg_name_type.__schema__ = {"type": "string", "pattern": __pkg_name_match.pattern}


def pkg_version_type(value: Any) -> str:
    """Package version validator."""

    value = __get_string(value)
    if not __pkg_VR_match.search(value):
        raise ValueError("Invalid package version: {0}".format(value))
    return value

pkg_version_type.__schema__ = {"type": "string", "pattern": __pkg_VR_match.pattern}


def pkg_release_type(value: Any) -> str:
    """Package release validator."""

    value = __get_string(value)
    if not __pkg_VR_match.search(value):
        raise ValueError("Invalid package release: {0}".format(value))
    return value

pkg_release_type.__schema__ = {"type": "string", "pattern": __pkg_VR_match.pattern}


def branch_name_type(value: Any) -> str:
    """Branch name validator."""

    value = __get_string(value)
    if value not in __known_branches:
        raise ValueError("Invalid branch name: {0}".format(value))
    return value

branch_name_type.__schema__ = {"type": "string"}


def arch_name_type(value: Any) -> str:
    """Architecture name validator."""

    value = __get_string(value)
    if value not in __known_archs:
        raise ValueError("Invalid architecure name: {0}".format(value))
    return value

arch_name_type.__schema__ = {"type": "string"}


def pkg_groups_type(value: Any) -> str:
    """Package category validator."""

    value = __get_string(value)
    if not __pkg_groups_match.search(value):
        raise ValueError("Invalid package category: {0}".format(value))
    return value

pkg_groups_type.__schema__ = {"type": "string", "pattern": __pkg_groups_match.pattern}


def packager_email_type(value: Any) -> str:
    """Packager email validator."""

    value = __get_string(value)
    if not __packager_email_match.search(value):
        raise ValueError("Invalid packager's email: {0}".format(value))
    return value

packager_email_type.__schema__ = {"type": "string", "pattern": __packager_email_match.pattern}


def packager_name_type(value: Any) -> str:
    """Packager name validator."""

    value = __get_string(value)
    if not __packager_name_match.search(value):
        raise ValueError("Invalid packager's name: {0}".format(value))
    return value

packager_name_type.__schema__ = {"type": "string", "pattern": __packager_name_match.pattern}


def packager_nick_type(value: Any) -> str:
    """Packager nickname validator."""

    value = __get_string(value)
    if not __packager_nickname_match.search(value):
        raise ValueError("Invalid packager's nickname: {0}".format(value))
    return value

packager_nick_type.__schema__ = {"type": "string", "pattern": __packager_nickname_match.pattern}


def maintainer_nick_type(value: Any) -> str:
    """Maintainer nickname validator."""

    value = __get_string(value)
    if not __packager_nickname_match.search(value):
        raise ValueError("Invalid maintainer's nickname: {0}".format(value))
    return value

maintainer_nick_type.__schema__ = {"type": "string", "pattern": __packager_nickname_match.pattern}


def checksum_type(value: Any) -> str:
    """Checksum hexadecimal string validator."""

    value = __get_string(value)
    if not __pkg_cs_match.search(value):
        raise ValueError("Invalid checksum hexadecimal string: {0}".format(value))
    return value

checksum_type.__schema__ = {"type": "string", "pattern": __pkg_cs_match.pattern}


def disttag_type(value: Any) -> str:
    """Disttag string validator."""

    value = __get_string(value)
    if not __pkg_disttag_match.search(value):
        raise ValueError("Invalid Disttag string: {0}".format(value))
    return value

disttag_type.__schema__ = {"type": "string", "pattern": __pkg_disttag_match.pattern}


def file_name_wc_type(value: Any) -> str:
    """File name with wildcards validator."""

    value = __get_string(value)
    if not __file_name_wc_match.search(value):
        raise ValueError("Invalid file name: {0}".format(value))
    return value

file_name_wc_type.__schema__ = {"type": "string", "pattern": __file_name_wc_match.pattern}


def dp_name_type(value: Any) -> str:
    """Dependency name validator."""

    value = __get_string(value)
    if not __dp_name_match.search(value):
        raise ValueError("Invalid dependency name: {0}".format(value))
    return value

dp_name_type.__schema__ = {"type": "string", "pattern": __dp_name_match.pattern}


def date_string_type(value: Any) -> datetime.datetime:
    """Date as YYYY-MM-DD string validator."""

    value = __get_string(value)
    try:
        as_date = datetime.datetime.strptime(value, "%Y-%m-%d")
        return as_date
    except ValueError:
        raise ValueError("Invalid date: {0}".format(value))

date_string_type.__schema__ = {"type": "string", "format": "date"}
