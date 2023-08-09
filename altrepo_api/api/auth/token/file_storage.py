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

from typing import Any, Optional, Union


class FileStorage:
    def delete(self, name: str) -> None:
        """Deletes value from storage by name."""
        raise NotImplementedError

    def map_delete(self, name: str, key: str) -> None:
        """Deletes value from mapping in storage by name and key."""
        raise NotImplementedError

    def map_getall(self, name: str) -> dict[str, str]:
        """Retrives mapping from storage by name."""
        raise NotImplementedError

    def map_get(self, name: str, key: str) -> Union[str, None]:
        """Retrives mapping value from storage by name and key."""
        raise NotImplementedError

    def map_set(
        self,
        name: str,
        mapping: dict[str, Any],
        expire: Optional[int] = None,
    ) -> None:
        """Saves mapping to storage and set expiration time."""
        raise NotImplementedError
