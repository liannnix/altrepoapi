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

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

from altrepo_api.api.misc import lut

from .oval_definitions.utils import make_sub_element


ALT_LINUX_COPYRIGHT = f"Copyright {datetime.now().year} BaseALT Ltd."
ALT_LINUX_ADVISORY_FROM = "errata.altlinux.org"
BUGZILLA_BASE_URL = lut.bugzilla_base
BDU_ID_TYPE = "BDU"
BDU_ID_PREFIX = f"{BDU_ID_TYPE}:"
CVE_ID_TYPE = "CVE"
CVE_ID_PREFIX = f"{CVE_ID_TYPE}-"


class Severity(Enum):
    NONE = "None"
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


@dataclass
class Vulnerability:
    id: str
    cvss: str
    cvss3: str
    href: str
    impact: type[Severity]
    cwe: Optional[str] = None
    public: Optional[datetime] = None

    def to_xml(self) -> xml.Element:
        if self.id.startswith(CVE_ID_PREFIX):
            cls = "cve"
        elif self.id.startswith(BDU_ID_PREFIX):
            cls = "bdu"
        else:
            cls = "vuln"

        r = xml.Element(cls)
        r.text = self.id
        if self.cvss:
            r.set("cvss", self.cvss)
        if self.cvss3:
            r.set("cvss3", self.cvss3)
        if self.cwe is not None:
            r.set("cwe", self.cwe)
        r.set("href", self.href)
        r.set("impact", str(self.impact.value))
        if self.public is not None:
            r.set("public", self.public.strftime("%Y%m%d"))
        return r


@dataclass
class Bugzilla:
    id: int
    summary: str
    href: str = field(init=False)

    def __post_init__(self):
        self.href = f"{BUGZILLA_BASE_URL}/{self.id}"

    def to_xml(self) -> xml.Element:
        r = xml.Element("bugzilla")
        r.text = self.summary
        r.set("id", str(self.id))
        r.set("href", self.href)
        return r


@dataclass
class ALTLinuxAdvisory:
    severity: type[Severity]
    issued: datetime
    updated: datetime
    vuln: list[Vulnerability]
    bugzilla: list[Bugzilla]
    affected_cpe_list: list[str] = field(default_factory=list)
    rights: str = field(init=False, default=ALT_LINUX_COPYRIGHT)

    def to_xml(self) -> xml.Element:
        r = xml.Element("advisory")
        r.set("from", ALT_LINUX_ADVISORY_FROM)
        make_sub_element(r, "severity", str(self.severity.value))
        make_sub_element(r, "rights", self.rights)
        make_sub_element(r, "issued", "", {"date": self.issued.strftime("%Y-%m-%d")})
        make_sub_element(r, "updated", "", {"date": self.updated.strftime("%Y-%m-%d")})
        for vuln in self.vuln:
            r.append(vuln.to_xml())
        for bug in self.bugzilla:
            r.append(bug.to_xml())
        if self.affected_cpe_list:
            af = make_sub_element(r, "affected_cpe_list", "")
            for cpe in self.affected_cpe_list:
                make_sub_element(af, "cpe", cpe)
        return r
