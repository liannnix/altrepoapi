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
from flask_restx import reqparse

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
__packager_nickname_match = re.compile("^[\w]{2,}$")  # type: ignore
# file name match allows '*' wildcard symbol
__file_name_wc_match = re.compile("^[\w\-. \*]{2,}$")  # type: ignore
__dp_name_match = re.compile("^[\w\/\(\)\.\-]{2,}$")  # type: ignore

# custom validators
def pkg_name_type(value: str) -> str:
    """Package name validator."""

    if isinstance(value, str):
        if not __pkg_name_match.search(value):
            raise ValueError("Invalid package name: {0}".format(value))
        return value
    raise ValueError("Package name should be string 2 characters long at least")

pkg_name_type.__schema__ = {"type": "string"}


def pkg_version_type(value: str) -> str:
    """Package version validator."""

    if isinstance(value, str):
        if not __pkg_VR_match.search(value):
            raise ValueError("Invalid package version: {0}".format(value))
        return value
    raise ValueError("Package version should be string")

pkg_version_type.__schema__ = {"type": "string"}


def pkg_release_type(value: str) -> str:
    """Package release validator."""

    if isinstance(value, str):
        if not __pkg_VR_match.search(value):
            raise ValueError("Invalid package release: {0}".format(value))
        return value
    raise ValueError("Package release should be string")

pkg_release_type.__schema__ = {"type": "string"}


def branch_name_type(value: str) -> str:
    """Branch name validator."""

    if isinstance(value, str):
        if value not in __known_branches:
            raise ValueError("Invalid branch name: {0}".format(value))
        return value
    raise ValueError("Branch name should be string")

branch_name_type.__schema__ = {"type": "string"}


def arch_name_type(value: str) -> str:
    """Architecture name validator."""

    if isinstance(value, str):
        if value not in __known_archs:
            raise ValueError("Invalid architecure name: {0}".format(value))
        return value
    raise ValueError("Architecture name should be string")

arch_name_type.__schema__ = {"type": "string"}


def pkg_groups_type(value: str) -> str:
    """Package category validator."""

    if isinstance(value, str):
        if not __pkg_groups_match.search(value):
            raise ValueError("Invalid package category: {0}".format(value))
        return value
    raise ValueError("Package category should be string")

pkg_groups_type.__schema__ = {"type": "string"}


def packager_email_type(value: str) -> str:
    """Packager email validator."""

    if isinstance(value, str):
        if not __packager_email_match.search(value):
            raise ValueError("Invalid package's email: {0}".format(value))
        return value
    raise ValueError("Packager email should be string")

packager_email_type.__schema__ = {"type": "string", "format": "email"}


def packager_name_type(value: str) -> str:
    """Packager name validator."""

    if isinstance(value, str):
        if not __packager_name_match.search(value):
            raise ValueError("Invalid package's name: {0}".format(value))
        return value
    raise ValueError("Packager name should be string")

packager_name_type.__schema__ = {"type": "string", "format": "email"}


def packager_nick_type(value: str) -> str:
    """Packager nickname validator."""

    if isinstance(value, str):
        if not __packager_nickname_match.search(value):
            raise ValueError("Invalid package's nickname: {0}".format(value))
        return value
    raise ValueError("Packager nickname should be string")

packager_nick_type.__schema__ = {"type": "string", "format": "nickname"}


def checksum_type(value: str) -> str:
    """Checksum hexadecimal string validator."""

    if isinstance(value, str):
        if not __pkg_cs_match.search(value):
            raise ValueError("Invalid checksum hexadecimal string: {0}".format(value))
        return value
    raise ValueError("Checksum should be hexadecimal string")

checksum_type.__schema__ = {"type": "string", "format": "hexadecimal"}


def disttag_type(value: str) -> str:
    """Disttag string validator."""

    if isinstance(value, str):
        if not __pkg_disttag_match.search(value):
            raise ValueError("Invalid Disttag string: {0}".format(value))
        return value
    raise ValueError("Disttag should be string")

disttag_type.__schema__ = {"type": "string", "format": "disttag"}


def file_name_wc_type(value: str) -> str:
    """File name with wildcards validator."""

    if isinstance(value, str):
        if not __file_name_wc_match.search(value):
            raise ValueError("Invalid file name: {0}".format(value))
        return value
    raise ValueError("File name should be string")

file_name_wc_type.__schema__ = {"type": "string"}


def dp_name_type(value: str) -> str:
    """Dependency name validator."""

    if isinstance(value, str):
        if not __dp_name_match.search(value):
            raise ValueError("Invalid dependency name: {0}".format(value))
        return value
    raise ValueError("Dependency name should be string")

dp_name_type.__schema__ = {"type": "string", "format": "dependency name"}
