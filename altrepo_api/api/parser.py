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

import re
import datetime
from flask_restx import reqparse
from typing import Any

from altrepo_api.api.misc import lut


class ParserFactory:
    """Registers request parser argument items and builds RequestParser by list of items."""

    def __init__(self) -> None:
        self.items: list[tuple[str, dict[str, Any]]] = []
        self.lindex: int = 0

    def register_item(self, item_name: str, **kwargs) -> int:
        """Stores request parser item and returns it's index."""

        self.items.append((item_name, kwargs))
        self.lindex = len(self.items) - 1
        return self.lindex

    def build_parser(self, *items: int) -> reqparse.RequestParser:
        """Builds RequestParser instance from list of registered items."""

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
__known_archs_ext = set(lut.known_archs).union(("srpm",))
__known_repo_components = set(lut.known_repo_components)
__known_states = set(lut.known_states)
__known_branches = set(lut.known_branches)
__known_img_archs = set(lut.known_image_archs)
__known_img_editions = set(lut.known_image_editions)
__known_img_releases = set(lut.known_image_releases)
__known_img_variants = set(lut.known_image_variants)
__known_img_components = set(lut.known_image_components)
__known_img_platforms = set(lut.known_image_platform)
__known_img_types = set(lut.known_image_types)

# regex patterns
__pkg_cs_match = re.compile(r"^[a-fA-F0-9]+$")
__pkg_name_match = re.compile(r"^[\w\.\+\-]{2,}$")
__pkg_name_list_match = re.compile(r"^([\w\.\+\-]{2,}[,]?)+$")
__pkg_VR_match = re.compile(r"^[\w\.\+]+$")
__pkg_groups_match = re.compile(r"^[A-Z][a-zA-Z0-9\+\ \/-]+$")
__pkg_disttag_match = re.compile(r"^[a-z0-9\+\.]+$")
__packager_name_match = re.compile(r"^[a-zA-Z]+[\w\.\ \-\@]*$")
__packager_email_match = re.compile(r"^[\w\.\-]+@[\w\.\-]+$")
__packager_nickname_match = re.compile(r"^[\w\-]{2,}$")
# file name match allows '*' wildcard symbol
__file_name_wc_match = re.compile(
    r"^[\\\/\w\-\.\,\#\:\+\@\&\$\!\*\%\'\~\:\=\{\}\[\]\(\)]{2,}$"
)
__dp_name_match = re.compile(r"^[\w\/\(\)\.\:\-\+]{2,}$")
# image name
__uuid_string_match = re.compile(
    r"^[0-9a-f]{8}\-[0-9a-f]{4}\-[0-9a-f]{4}\-[0-9a-f]{4}\-[0-9a-f]{12}$"
)
__image_file_match = re.compile(r"^[a-zA-Z0-9\-\.\_:]+$")
__image_tag_match = re.compile(r"^[a-zA-Z0-9\-\.\_:]+:[a-z]+$")
__image_version_match = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
__image_flavor_match = re.compile(r"^[a-zA-Z\-]+$")
# licenses
__license_string_match = re.compile(r"^[A-Za-z0-9\(\)\+ .\-/&,]+$")
__license_id_match = re.compile(r"^[A-Za-z0-9\-\.\+]+$")
# acl
__acl_group_match = re.compile(r"^@?[a-z0-9\_]+$")
# task search
__task_search_match = re.compile(r"^(@?[\w\.\+\-\_:#]{2,},?)+$")
# file search
__file_search_match = re.compile(r"^[\w\/\.\+\- $#%:=@\{\}]{3,}$")
# package vulnerabilities
__pkgs_open_vulns_search_match = re.compile(r"^([\w\.\+\-\_:]{2,},?)+$")
# vulnerabilities
__cve_id_match = re.compile(r"^CVE-\d{4}-\d{4,}$")
__cve_id_list_match = re.compile(r"^(CVE-\d{4}-\d{4,},?)+$")
__bdu_id_match = re.compile(r"^BDU:\d{4}-\d{5}$")
__bdu_id_list_match = re.compile(r"^(BDU:\d{4}-\d{5},?)+$")
__errata_id_match = re.compile(r"^ALT-[A-Z]+-2\d{3}-\d{4,}-\d{1,}$")
__errata_search_match = re.compile(r"^([\w\.\+\-\_:]{2,},?)+$")
__password_match = re.compile(r"^([\w|\W]+)$")
__cpe_search_match = re.compile(r"^([\w\.\+\-\_:*]{2,},?)+$")
# input
__positive_integer = re.compile(r"^(?<![-.])\b[0-9]+\b(?!\.[0-9])$")
__sort_match = re.compile(r"^-?([a-z\_]{2,},?)+$")
# package name conversion
__project_name_match = re.compile(r"^[\w\.\+\-\:]{2,}$")


# custom validators
def __get_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValueError("{0} is not a valid integer".format(value))


def __get_string(value: Any) -> str:
    try:
        return str(value)
    except (TypeError, ValueError):
        raise ValueError("{0} is not a valid string".format(value))


MIN_TASK_ID = 1
MAX_TASK_ID = 4_000_000_000


def task_id_type(value: Any) -> int:
    """Task ID validator."""

    value = __get_int(value)
    if value < MIN_TASK_ID or value > MAX_TASK_ID:
        raise ValueError("Invalid task ID: {0}".format(value))
    return value


task_id_type.__schema__ = {
    "type": "integer",
    "minimum": MIN_TASK_ID,
    "maximum": MAX_TASK_ID,
}


def pkg_name_type(value: Any) -> str:
    """Package name validator."""

    value = __get_string(value)
    if not __pkg_name_match.search(value):
        raise ValueError("Invalid package name: {0}".format(value))
    return value


pkg_name_type.__schema__ = {"type": "string", "pattern": __pkg_name_match.pattern}


def pkg_name_list_type(value: Any) -> str:
    """Package name validator."""

    value = __get_string(value)
    if not __pkg_name_list_match.search(value):
        raise ValueError("Invalid package name: {0}".format(value))
    return value


pkg_name_list_type.__schema__ = {
    "type": "string",
    "pattern": __pkg_name_list_match.pattern,
}


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
        raise ValueError("Invalid architecture name: {0}".format(value))
    return value


arch_name_type.__schema__ = {"type": "string"}


# __known_archs_ext
def arch_name_type_ext(value: Any) -> str:
    """Extended architecture name validator that includes virtual 'srpm' one."""

    value = __get_string(value)
    if value not in __known_archs_ext:
        raise ValueError("Invalid architecture name: {0}".format(value))
    return value


arch_name_type_ext.__schema__ = {"type": "string"}


def arch_component_name_type(value: Any) -> str:
    """Architecture name validator for component."""

    value = __get_string(value)
    archs = __known_archs.copy()
    archs.add("srpm")
    if value not in archs:
        raise ValueError("Invalid architecture name: {0}".format(value))
    return value


arch_component_name_type.__schema__ = {"type": "string"}


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


packager_email_type.__schema__ = {
    "type": "string",
    "pattern": __packager_email_match.pattern,
}


def packager_name_type(value: Any) -> str:
    """Packager name validator."""

    value = __get_string(value)
    if not __packager_name_match.search(value):
        raise ValueError("Invalid packager's name: {0}".format(value))
    return value


packager_name_type.__schema__ = {
    "type": "string",
    "pattern": __packager_name_match.pattern,
}


def packager_nick_type(value: Any) -> str:
    """Packager nickname validator."""

    value = __get_string(value)
    if not __packager_nickname_match.search(value):
        raise ValueError("Invalid packager's nickname: {0}".format(value))
    return value


packager_nick_type.__schema__ = {
    "type": "string",
    "pattern": __packager_nickname_match.pattern,
}


def maintainer_nick_type(value: Any) -> str:
    """Maintainer nickname validator."""

    value = __get_string(value)
    if not __packager_nickname_match.search(value):
        raise ValueError("Invalid maintainer's nickname: {0}".format(value))
    return value


maintainer_nick_type.__schema__ = {
    "type": "string",
    "pattern": __packager_nickname_match.pattern,
}


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


file_name_wc_type.__schema__ = {
    "type": "string",
    "pattern": __file_name_wc_match.pattern,
}


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


def datetime_string_type(value: Any) -> datetime.datetime:
    """ISO-8601 datetime validator."""

    value = __get_string(value)
    try:
        as_datetime = datetime.datetime.fromisoformat(value)
        return as_datetime
    except ValueError:
        raise ValueError("Invalid datetime: {0}".format(value))


datetime_string_type.__schema__ = {"type": "string", "format": "datetime"}


def uuid_type(value: Any) -> str:
    """UUID string validator."""

    value = __get_string(value)
    if not __uuid_string_match.search(value):
        raise ValueError("Invalid UUID string: {0}".format(value))
    return value


uuid_type.__schema__ = {"type": "string", "pattern": __uuid_string_match.pattern}


def image_tag_type(value: Any) -> str:
    """Image name validator."""

    value = __get_string(value)
    if not __image_tag_match.search(value):
        raise ValueError("Invalid image name: {0}".format(value))
    return value


image_tag_type.__schema__ = {"type": "string", "pattern": __image_tag_match.pattern}


def image_file_type(value: Any) -> str:
    """Image name validator."""

    value = __get_string(value)
    if not __image_file_match.search(value):
        raise ValueError("Invalid image name: {0}".format(value))
    return value


image_file_type.__schema__ = {"type": "string", "pattern": __image_file_match.pattern}


def image_version_type(value: Any) -> str:
    """Image version validator."""

    value = __get_string(value)
    if not __image_version_match.search(value):
        raise ValueError("Invalid image version: {0}".format(value))
    return value


image_version_type.__schema__ = {
    "type": "string",
    "pattern": __image_version_match.pattern,
}


def img_edition_type(value: Any) -> str:
    """Image edition validator."""

    value = __get_string(value)
    if value not in __known_img_editions:
        raise ValueError("Invalid image edition: {0}".format(value))
    return value


img_edition_type.__schema__ = {"type": "string"}


def img_arch_type(value: Any) -> str:
    """Image architecture validator."""

    value = __get_string(value)
    if value not in __known_img_archs:
        raise ValueError("Invalid image architecture: {0}".format(value))
    return value


img_arch_type.__schema__ = {"type": "string"}


def img_variant_type(value: Any) -> str:
    """Image variant validator."""

    value = __get_string(value)
    if value not in __known_img_variants:
        raise ValueError("Invalid image variant: {0}".format(value))
    return value


img_variant_type.__schema__ = {"type": "string"}


def img_component_type(value: Any) -> str:
    """Image component validator."""

    value = __get_string(value)
    if value not in __known_img_components:
        raise ValueError("Invalid image component: {0}".format(value))
    return value


img_component_type.__schema__ = {"type": "string"}


def img_platform_type(value: Any) -> str:
    """Image platform validator."""

    value = __get_string(value)
    if value not in __known_img_platforms:
        raise ValueError("Invalid image platform: {0}".format(value))
    return value


img_platform_type.__schema__ = {"type": "string"}


def img_flavor_type(value: Any) -> str:
    """Image flavor validator."""

    value = __get_string(value)
    if not __image_flavor_match.search(value):
        raise ValueError("Invalid image flavor: {0}".format(value))
    return value


img_flavor_type.__schema__ = {"type": "string"}


def img_release_type(value: Any) -> str:
    """Image release validator."""

    value = __get_string(value)
    if value not in __known_img_releases:
        raise ValueError("Invalid image release: {0}".format(value))
    return value


img_release_type.__schema__ = {"type": "string"}


def img_type(value: Any) -> str:
    """Image type validator."""

    value = __get_string(value)
    if value not in __known_img_types:
        raise ValueError("Invalid image type: {0}".format(value))
    return value


img_type.__schema__ = {"type": "string"}


def license_string_type(value: Any) -> str:
    """License string validator."""

    value = __get_string(value)
    if not __license_string_match.search(value):
        raise ValueError("Invalid license string: {0}".format(value))
    return value


license_string_type.__schema__ = {
    "type": "string",
    "pattern": __license_string_match.pattern,
}


def license_id_type(value: Any) -> str:
    """License ID validator."""

    value = __get_string(value)
    if not __license_id_match.search(value):
        raise ValueError("Invalid license string: {0}".format(value))
    return value


license_id_type.__schema__ = {"type": "string", "pattern": __license_id_match.pattern}


def acl_group_type(value: Any) -> str:
    """ACL group validator."""

    value = __get_string(value)
    if not __acl_group_match.search(value):
        raise ValueError("Invalid ACL group: {0}".format(value))
    return value


acl_group_type.__schema__ = {"type": "string", "pattern": __acl_group_match.pattern}


def task_search_type(value: Any) -> str:
    """Task search validator."""

    value = __get_string(value)
    if not __task_search_match.search(value):
        raise ValueError("Invalid input: {0}".format(value))
    return value


task_search_type.__schema__ = {"type": "string", "pattern": __task_search_match.pattern}


def task_state_type(value: Any) -> str:
    """Task state validator."""

    value = __get_string(value)
    if value.upper() not in __known_states:
        raise ValueError("Invalid task_state: {0}".format(value))
    return value


task_state_type.__schema__ = {"type": "string"}


def file_search_type(value: Any) -> str:
    """File search validator."""

    value = __get_string(value)
    if not __file_search_match.search(value):
        raise ValueError("Invalid input: {0}".format(value))
    return value


file_search_type.__schema__ = {"type": "string", "pattern": __file_search_match.pattern}


def repo_component_type(value: Any) -> str:
    """Repository component validator."""

    value = __get_string(value)
    if value not in __known_repo_components:
        raise ValueError("Invalid architecture name: {0}".format(value))
    return value


repo_component_type.__schema__ = {"type": "string"}


def cve_id_type(value: Any) -> str:
    """CVE id validator."""

    value = __get_string(value)
    if not __cve_id_match.search(value):
        raise ValueError("Invalid input: {0}".format(value))
    return value


cve_id_type.__schema__ = {"type": "string", "pattern": __cve_id_match.pattern}


def cve_id_list_type(value: Any) -> str:
    """CVE id list validator."""

    value = __get_string(value)
    if not __cve_id_list_match.search(value):
        raise ValueError("Invalid input: {0}".format(value))
    return value


cve_id_list_type.__schema__ = {"type": "string", "pattern": __cve_id_list_match.pattern}


def bdu_id_type(value: Any) -> str:
    """BDU id validator."""

    value = __get_string(value)
    if not __bdu_id_match.search(value):
        raise ValueError("Invalid input: {0}".format(value))
    return value


bdu_id_type.__schema__ = {"type": "string", "pattern": __bdu_id_match.pattern}


def bdu_id_list_type(value: Any) -> str:
    """BDU id list validator."""

    value = __get_string(value)
    if not __bdu_id_list_match.search(value):
        raise ValueError("Invalid input: {0}".format(value))
    return value


bdu_id_list_type.__schema__ = {"type": "string", "pattern": __bdu_id_list_match.pattern}


def errata_id_type(value: Any) -> str:
    """Errata id validator."""

    value = __get_string(value)
    if not __errata_id_match.search(value):
        raise ValueError("Invalid input: {0}".format(value))
    return value


errata_id_type.__schema__ = {"type": "string", "pattern": __errata_id_match.pattern}


def errata_search_type(value: Any) -> str:
    """Errata search validator."""

    value = __get_string(value)
    if not __errata_search_match.search(value):
        raise ValueError("Invalid input: {0}".format(value))
    return value


errata_search_type.__schema__ = {
    "type": "string",
    "pattern": __errata_search_match.pattern,
}


def password_type(value: Any) -> str:
    """Password validator."""

    value = __get_string(value)
    if not __password_match.search(value):
        raise ValueError("Invalid password: {0}".format(value))
    return value


password_type.__schema__ = {
    "type": "string",
    "pattern": __password_match.pattern,
    "format": "password",
}


def positive_integer_type(value: Any) -> int:
    """Positive integer validator."""

    value = __get_string(value)
    if not __positive_integer.search(value):
        raise ValueError("Invalid positive integer: {0}".format(value))
    return int(value)


positive_integer_type.__schema__ = {
    "type": "integer",
    "pattern": __positive_integer.pattern,
}


def sort_type(value: Any) -> str:
    """Sort validator."""

    value = __get_string(value)
    if not __sort_match.search(value):
        raise ValueError("Invalid input: {0}".format(value))
    return value


sort_type.__schema__ = {
    "type": "string",
    "pattern": __sort_match.pattern,
}


def open_vulns_search_type(value: Any) -> str:
    """Validator for searching packages with open vulnerabilities."""

    value = __get_string(value)
    if not __pkgs_open_vulns_search_match.search(value):
        raise ValueError("Invalid input: {0}".format(value))
    return value


open_vulns_search_type.__schema__ = {
    "type": "string",
    "pattern": __pkgs_open_vulns_search_match.pattern,
}


def cpe_search_type(value: Any) -> str:
    """Validator for searching cpes."""

    value = __get_string(value)
    if not __cpe_search_match.search(value):
        raise ValueError("Invalid input: {0}".format(value))
    return value


cpe_search_type.__schema__ = {
    "type": "string",
    "pattern": __cpe_search_match.pattern,
}


def project_name_type(value: Any) -> str:
    """Project name validator."""

    value = __get_string(value)
    if not __project_name_match.search(value):
        raise ValueError("Invalid project name: {0}".format(value))
    return value


project_name_type.__schema__ = {
    "type": "string",
    "pattern": __project_name_match.pattern,
}
