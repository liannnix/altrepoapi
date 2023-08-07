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
from functools import cached_property
from math import ceil


class Paginator:

    def __init__(self, object_list: list, limit: int):
        self.object_list = object_list
        self.limit = int(limit) if limit and int(limit) > 0 else self.count

    def validate_page_number(self, number):
        """Validate page number."""
        try:
            number = int(number)
        except (TypeError, ValueError):
            number = 1
        if number < 1:
            number = 1
        if number > self.num_pages:
            if number != 1:
                number = self.num_pages
        return number

    @cached_property
    def count(self) -> int:
        """Return the total number of objects."""
        return len(self.object_list)

    @cached_property
    def num_pages(self) -> int:
        """Return the total number of pages."""
        if self.count == 0:
            return 0
        hits = max(1, self.count)
        return ceil(hits / self.limit)

    def page(self, to_page: int) -> list:
        bottom = (to_page - 1) * self.limit
        top = bottom + self.limit
        if top >= self.count:
            top = self.count
        return self.object_list[bottom:top]

    def get_page(self, to_page: int) -> page:
        page_number = self.validate_page_number(to_page)
        return self.page(page_number)

