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

import re


reDefinitionIDPattern = re.compile(r"oval:[A-Za-z0-9_\-\.]+:def:[1-9][0-9]*")
reObjectIDPattern = re.compile(r"oval:[A-Za-z0-9_\-\.]+:obj:[1-9][0-9]*")
reStateIDPattern = re.compile(r"oval:[A-Za-z0-9_\-\.]+:ste:[1-9][0-9]*")
reTestIDPattern = re.compile(r"oval:[A-Za-z0-9_\-\.]+:tst:[1-9][0-9]*")
reVariableIDPattern = re.compile(r"oval:[A-Za-z0-9_\-\.]+:var:[1-9][0-9]*")

DefinitionIDPattern = str
VariableIDPattern = str
ObjectIDPattern = str
StateIDPattern = str
TestIDPattern = str
ItemIDPattren = int  # unsigned int!
