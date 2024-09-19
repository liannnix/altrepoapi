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
from flask_restx import inputs

from altrepo_api.api.parser import (
    parser,
    branch_name_type,
    task_search_type,
    task_state_type,
    packager_nick_type,
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
    default=10,
    help="number of last tasks to get",
    location="args",
)
task_limit_100_opt = parser.register_item(
    "tasks_limit",
    type=int,
    required=False,
    default=100,
    help="number of last tasks to get",
    location="args",
)
state_opt = parser.register_item(
    "state",
    type=task_state_type,
    action="split",
    required=False,
    help="task state",
    location="args",
)
owner_opt = parser.register_item(
    "owner",
    type=packager_nick_type,
    required=False,
    help="task owner",
    location="args",
)
input_val = parser.register_item(
    "input",
    type=task_search_type,
    action="split",
    required=True,
    help="task search arguments",
    location="args",
)
by_package_opt = parser.register_item(
    "by_package",
    type=inputs.boolean,
    required=False,
    help="find tasks by source package name",
    location="args",
    default=False,
)


# build parsers
last_tasks_args = parser.build_parser(branch_opt, task_limit_opt)
find_tasks_args = parser.build_parser(
    input_val, owner_opt, branch_opt, state_opt, task_limit_100_opt, by_package_opt
)
find_tasks_lookup_args = parser.build_parser(input_val, branch_opt, task_limit_opt)
