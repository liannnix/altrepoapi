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

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Union


@dataclass
class Task:
    id: int
    branch: str
    package: str


@dataclass
class TaskHistory:
    id: int
    prev: int
    branch: str
    changed: datetime


@dataclass
class PackageMeta:
    pkghash: str
    name: str
    branch: str
    version: str
    release: str


@dataclass
class PackageScheme(PackageMeta):
    errata_id: str
    task_id: int
    subtask_id: int
    task_state: str
    last_version: Union[PackageMeta, None] = None

    def asdict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ExcludedPackagesSchema(PackageMeta):
    vuln_id: str
    cpe: str
    cpe_hash: int
