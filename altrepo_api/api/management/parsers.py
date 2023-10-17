# ALTRepo API
# Copyright (C) 2021-2023  BaseALT Ltd

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
    errata_id_type,
    positive_integer_type,
    task_search_type,
)

input_val_opt = parser.register_item(
    "input",
    type=task_search_type,
    action="split",
    required=False,
    help="task search arguments",
    location="args",
)
branch_name_opt = parser.register_item(
    "branch", type=branch_name_type, required=False, help="branch name", location="args"
)
limit_opt = parser.register_item(
    "limit",
    type=positive_integer_type,
    required=False,
    help="number of records",
    location="args",
)
page_opt = parser.register_item(
    "page",
    type=positive_integer_type,
    required=False,
    help="number page",
    location="args",
)
errata_id = parser.register_item(
    "errata_id",
    type=errata_id_type,
    required=True,
    help="errata ID",
    location="args"
)
is_errata_opt = parser.register_item(
    "is_errata",
    type=inputs.boolean,
    default=False,
    required=False,
    help="is errata",
    location="args",
)

task_list_args = parser.build_parser(
    input_val_opt, branch_name_opt, is_errata_opt, page_opt, limit_opt
)
errata_manage_get_args = parser.build_parser(errata_id)
