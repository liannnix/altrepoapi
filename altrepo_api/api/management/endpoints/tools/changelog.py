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
from datetime import datetime
from typing import NamedTuple


class ChangelogRecord(NamedTuple):
    date: datetime
    name: str
    evr: str
    text: str


class PackageChangelog(NamedTuple):
    hash: int
    changelog: list[ChangelogRecord]


_VULN_REGEX = (
    r"("
    r"CVE-\d{4}-\d{4,}|"
    r"BDU:\d{4}-\d{5}|"
    r"OVE-\d{8}-\d{4}|"
    r"MFSA[- ]+\d{4}-\d{2}"
    r")"
)
VULN_RE = re.compile(_VULN_REGEX, re.IGNORECASE)
EVR_RE = re.compile(r"^\d+:[\w\.\-]+$")


def _mentioned_vulns(chagelog: str) -> list[str]:
    return sorted({m.upper() for m in VULN_RE.findall(chagelog)})


def vulns_from_pkg_changelog(package_changelog: PackageChangelog) -> list[list[str]]:
    return [_mentioned_vulns(c.text) for c in package_changelog.changelog]


def split_evr(evr: str) -> tuple[int, str, str]:
    epoch, version, release = 0, "", ""

    if EVR_RE.match(evr):
        _epoch = evr.split(":")[0]
        _evr = evr.lstrip(f"{_epoch}:").split("-")
        epoch = int(_epoch)
    else:
        _evr = evr.split("-")

    version = "-".join(_evr[:-1])
    release = _evr[-1]

    return epoch, version, release
