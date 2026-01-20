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

from enum import Enum
from typing import Any


def check_val_in_enum(v: Any, e: type[Enum]) -> bool:
    return v in {x.value for x in e}  # type: ignore


class CheckEnumeration(Enum):
    all = "all"
    at_least_one = "at least one"
    none_exist = "none exist"
    none_satisfy = "none satisfy"
    only_one = "only one"


class ClassEnumeration(Enum):
    compliance = "compliance"
    inventroy = "inventroy"
    miscellaneous = "miscellaneous"
    patch = "patch"
    vulnerability = "vulnerability"


class SimpleDatatypeEnumeration(Enum):
    int = "int"
    float = "float"
    binary = "binary"
    string = "string"
    boolean = "boolean"
    version = "version"
    evr_string = "evr_string"
    fileset_revision = "fileset_revision"
    ios_version = "ios_version"
    ipv4_address = "ipv4_address"
    ipv6_address = "ipv6_address"


class ComplexDatatypeEnumeration(Enum):
    record = "record"


class DatatypeEnumeration(Enum):
    int = "int"
    float = "float"
    binary = "binary"
    string = "string"
    boolean = "boolean"
    version = "version"
    evr_string = "evr_string"
    fileset_revision = "fileset_revision"
    ios_version = "ios_version"
    ipv4_address = "ipv4_address"
    ipv6_address = "ipv6_address"
    record = "record"


class ResultEnumeration(Enum):
    true = "true"
    false = "false"
    error = "error"
    unknown = "unknown"
    not_evaluated = "not evaluated"
    not_applicable = "not applicable"


class ExistenceEnumeration(Enum):
    all_exist = "all_exist"
    any_exist = "any_exist"
    at_least_one_exists = "at_least_one_exists"
    none_exist = "none_exist"
    only_one_exists = "only_one_exists"


class FamilyEnumeration(Enum):
    catos = "catos"
    ios = "ios"
    macos = "macos"
    pixos = "pixos"
    unix = "unix"
    windows = "windows"
    undefined = "undefined"
    vmware_infrastructure = "vmware_infrastructure"


class OperationEnumeration(Enum):
    equals = "equals"
    not_equal = "not equal"
    case_insensitive_equals = "case insensitive equals"
    case_insensitive_not_equal = "case insensitive not equal"
    greater_than = "greater than"
    less_than = "less than"
    greater_than_or_equal = "greater than or equal"
    less_than_or_equal = "less than or equal"
    bitwise_and = "bitwise and"
    bitwise_or = "bitwise or"
    pattern_match = "pattern match"
    subset_of = "subset of"
    superset_of = "superset of"


class OperatorEnumeration(Enum):
    AND = "AND"
    ONE = "ONE"
    OR = "OR"
    XOR = "XOR"


class FilterActionEnumeration(Enum):
    include = "include"
    exclude = "exclude"
