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

import xml.etree.ElementTree as xml

from datetime import datetime
from typing import Any


def bool_to_xml(b: bool) -> str:
    return "true" if b else "false"


def value_to_xml(val: Any, tag: str) -> xml.Element:
    if isinstance(val, xml.Element):
        return val

    if hasattr(val, "to_xml"):
        return val.to_xml()

    r = xml.Element(tag)

    if isinstance(val, str):
        r.text = val
    elif type(val) in (int, float, bool):
        r.text = str(val)
    elif isinstance(val, datetime):
        r.text = val.isoformat()
    else:
        # default convert to string
        r.text = str(val)

    return r


def extension_point_to_xml(ext: Any) -> xml.Element:
    return value_to_xml(ext, "extension_point")


def make_sub_element(
    parent: xml.Element, tag: str, text: str, attributes: dict[str, str] = dict()
) -> xml.Element:
    child = xml.SubElement(parent, tag, attributes)
    if text:
        child.text = text
    return child
