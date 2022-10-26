# ALTRepo API
# Copyright (C) 2021-2022  BaseALT Ltd

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

from altrepo_api.api.parser import (
    parser,
    branch_name_type,
)


# register parser items
branch_opt = parser.register_item(
    "branch",
    type=branch_name_type,
    required=False,
    help="name of packageset",
    location="args",
)
task_limit_opt = parser.register_item(
    "tasks_limit",
    type=int,
    required=False,
    help="number of last tasks to get",
    location="args",
)


# build parsers
last_tasks_args = parser.build_parser(branch_opt, task_limit_opt)
