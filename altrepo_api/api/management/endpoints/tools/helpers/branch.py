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

from datetime import datetime
from typing import Union

from .base import _pManageErrata
from ..base import Branch, Task, TaskInfo


def find_closest_branch_state(
    cls: _pManageErrata, task_changed: datetime
) -> Union[Branch, None]:
    """Finds closest branch state by given task."""

    cls.status = False
    branch = cls.errata.pkgset_name
    task_id = cls.errata.task_id

    # get DONE tasks history
    response = cls.send_sql_request(
        cls.sql.get_done_tasks.format(branch=branch, changed=task_changed)
    )
    if not cls.sql_status:
        return None
    if not response:
        _ = cls.store_error(
            {
                "message": f"Failed to get 'DONE' tasks history for branch {branch} from {task_id}"
            }
        )

    tasks = {t.id: t for t in (Task(*el) for el in response)}
    if task_id not in tasks:
        _ = cls.store_error(
            {
                "message": f"Task {task_id} not found in 'DONE' tasks history for {branch}"
            }
        )

    # get nearest branch point
    response = cls.send_sql_request(
        cls.sql.get_nearest_branch_point.format(branch=branch, changed=task_changed)
    )
    if not cls.sql_status:
        return None
    if not response:
        # handle this case on caller side
        cls.status = True
        return None

    branch_state = Branch(*response[0])
    if branch_state.task not in tasks:
        _ = cls.store_error(
            {"message": "Branch state is inconsistent with task history"},
            severity=cls.LL.ERROR,  # type: ignore
        )
        return None

    cls.status = True
    return branch_state


def get_last_branch_state(cls: _pManageErrata) -> Union[Branch, None]:
    """gets last branch state by given task."""

    cls.status = False
    branch = cls.errata.pkgset_name

    # get last commited branch state
    response = cls.send_sql_request(cls.sql.get_last_branch_state.format(branch=branch))
    if not cls.sql_status:
        return None
    if not response:
        _ = cls.store_error({"message": f"Failed to find last state for {branch}"})
        return None

    cls.status = True
    return Branch(*response[0])


def get_task_info(cls: _pManageErrata) -> Union[tuple[TaskInfo, datetime], None]:
    cls.status = False

    response = cls.send_sql_request(
        cls.sql.get_package_info_by_task_and_subtask.format(
            task_id=cls.errata.task_id, subtask_id=cls.errata.subtask_id
        )
    )
    if not cls.sql_status:
        return None
    if not response:
        _ = cls.store_error(
            {
                "message": "No data found in DB for given task and subtask",
                "errata": cls.errata.asdict(),
            }
        )
        return None

    cls.status = True
    return TaskInfo(*response[0][:-1]), response[0][-1]
