# ALTRepo API
# Copyright (C) 2021-2025  BaseALT Ltd

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

import os
import json
import time
import errno

from pathlib import Path
from datetime import datetime
from typing import Any, Literal, Optional, TypedDict, Union

from altrepo_api.utils import get_logger


logger = get_logger(__name__)

LOCK_FILE_DIR = ".filestorage"
LOCK_FILE_NAME = ".filestorage.lock"
LOCK_FILE_TIMEOUT = 30
STORAGE_FILE_NAME = "filestorage.json"


ValueType = Union[str, int, float, datetime, dict[str, Any], list[Any], None]
ValueTypeName = Literal["str", "int", "float", "datetime", "dict", "list"]


def get_workdir() -> Path:
    workdir = Path(os.path.expanduser("~")).joinpath(LOCK_FILE_DIR)

    if not workdir.exists():
        logger.warning(f"Filestorage directory {workdir!s} doesn't exist. Creating...")
        try:
            workdir.mkdir(mode=0o755, parents=True, exist_ok=True)
        except OSError:
            raise FileStorageError(f"Failed to create directory {workdir!s}")
    elif not workdir.is_dir():
        raise FileStorageError(f"{workdir!s} is not a valid directory")

    if not os.access(workdir, os.R_OK | os.W_OK | os.X_OK):
        raise FileStorageError(f"Insufficient permissions for {workdir!s} directory")

    return workdir


def value_to_storage(value: ValueType, type: ValueTypeName) -> Any:
    if type == "datetime":
        return value.isoformat()  # type: ignore
    return value


def value_from_storage(value: Any, type: ValueTypeName) -> ValueType:
    if type == "datetime":
        return datetime.fromisoformat(value)
    return value


class FileStorageError(Exception):
    pass


class FileStorage:
    def __init__(self) -> None:
        self.s = StorageHandler()

    def delete(self, name: str) -> None:
        """Deletes value from storage by name."""

        self.s.delete(name)

    def map_delete(self, name: str, key: str) -> None:
        """Deletes value from mapping in storage by name and key."""

        map: dict[str, Any] = self.s.get(name)  # type: ignore

        if map is None or key not in map:
            return None

        del map[key]
        self.s.set(name, "dict", map, None)

    def map_getall(self, name: str) -> dict[str, str]:
        """Retrives mapping from storage by name."""

        map: dict[str, str] = self.s.get(name)  # type: ignore
        return {} if map is None else map

    def map_get(self, name: str, key: str) -> Union[str, None]:
        """Retrives mapping value from storage by name and key."""

        map: dict[str, str] = self.s.get(name)  # type: ignore
        if map is None or key not in map:
            return None
        return map[key]

    def map_set(
        self,
        name: str,
        mapping: dict[str, Any],
        expire: Optional[int] = None,
    ) -> None:
        """Saves mapping to storage and set expiration time."""

        map: dict[str, Any] = self.s.get(name)  # type: ignore
        if map is None:
            self.s.set(name, "dict", mapping, expire)
        else:
            map.update(mapping)
            self.s.set(name, "dict", map, expire)


class RecordMeta(TypedDict):
    key: str
    type: ValueTypeName
    created: int
    updated: int
    expires: int


class Storage(TypedDict):
    meta: dict[str, RecordMeta]
    data: dict[str, Any]


EMPTY_STORAGE = Storage(meta={}, data={})


class StorageHandler:
    def __init__(self) -> None:
        self.file = get_workdir().joinpath(STORAGE_FILE_NAME)
        self.lock = FileLock()
        self.storage: Storage
        with self.lock:
            self._load_file()

    def _load_file(self) -> None:
        if not self.file.exists():
            logger.warning(f"{self.file!s} doesn't exist. Creating...")
            with self.file.open("wt") as f:
                json.dump(EMPTY_STORAGE, f)
            self.storage = EMPTY_STORAGE.copy()

        if not self.file.is_file():
            raise FileStorageError(f"Not a file {self.file!s}")

        try:
            data: dict[str, Any] = json.load(self.file.open("rt"))
            self.storage = Storage(meta=data.get("meta", {}), data=data.get("data", {}))
        except Exception as e:
            logger.error(f"Failed to load data from {self.file!s} due to {e}")
            raise FileStorageError(f"Failed to load data from {self.file!s}")

    def _save_file(self) -> None:
        try:
            with self.file.open("wt") as f:
                json.dump(self.storage, f)
        except Exception as e:
            logger.error(f"Failed to store data to {self.file!s} due to {e}")
            raise FileStorageError("Storage save error") from e

    def _remove_expired(self) -> None:
        self._load_file()

        now = datetime.now().timestamp()
        need_save = False

        for meta in list(self.storage["meta"].values()):
            key = meta["key"]
            last = max(meta["created"], meta["updated"])
            expires = meta["expires"]

            if expires <= 0:
                continue

            if now > (last + expires):
                need_save = True
                try:
                    del self.storage["meta"][key]
                    del self.storage["data"][key]
                except KeyError:
                    pass

        if need_save:
            self._save_file()

    def _meta_get_key(self, name: str) -> Union[str, None]:
        self._remove_expired()

        if name not in self.storage["meta"]:
            return None

        return name

    def _delete(self, name: str) -> None:
        # delete key meta and related value if exists
        if name not in self.storage["meta"] and name not in self.storage["data"]:
            return

        try:
            del self.storage["meta"][name]
            del self.storage["data"][name]
        except KeyError:
            pass

        self._save_file()

    def _create(
        self,
        name: str,
        type: ValueTypeName,
        value: ValueType,
        expires: Union[int, None],
    ) -> None:
        self.storage["meta"][name] = RecordMeta(
            key=name,
            created=int(datetime.now().timestamp()),
            updated=int(datetime.now().timestamp()),
            type=type,
            expires=expires if expires is not None else 0,
        )
        self.storage["data"][name] = value_to_storage(value, type)
        self._save_file()

    def _update(
        self,
        name: str,
        type: ValueTypeName,
        value: ValueType,
        expires: Union[int, None],
    ) -> None:
        meta = self.storage["meta"][name]
        # update metadata
        meta["updated"] = int(datetime.now().timestamp())
        meta["type"] = type
        if expires is not None:
            meta["expires"] = expires
        # store changes
        self.storage["meta"][name] = meta
        self.storage["data"][name] = value_to_storage(value, type)
        self._save_file()

    def get(self, name: str) -> ValueType:
        with self.lock:
            key = self._meta_get_key(name)

            if key is None:
                return None

            value_type = self.storage["meta"][key]["type"]
            value = self.storage["data"].get(key)

            return value_from_storage(value, value_type)

    def set(
        self,
        name: str,
        type: ValueTypeName,
        value: ValueType,
        expires: Union[int, None],
    ) -> None:
        with self.lock:
            action = self._create if self._meta_get_key(name) is None else self._update
            action(name, type, value, expires)

    def delete(self, name) -> None:
        with self.lock:
            key = self._meta_get_key(name)

            if key is None:
                return

            self._delete(name)


class FileLock:
    """File lock handler to be used as context manager."""

    def __init__(self) -> None:
        self._lockfile = get_workdir().joinpath(LOCK_FILE_NAME)
        self._is_locked = False
        self._timeout: int = LOCK_FILE_TIMEOUT

    def _acquire(self, wait: int = 0):
        if wait > 0:
            timeout = wait
        else:
            timeout = self._timeout

        start_time = time.time()
        while True:
            try:
                # Open file exclusively
                self.fd = os.open(self._lockfile, os.O_CREAT | os.O_EXCL | os.O_RDWR)
                break
            except OSError as e:
                if e.errno != errno.EEXIST:
                    raise
                if (time.time() - start_time) >= timeout:
                    raise TimeoutError("Lock acquire has timed out")
                time.sleep(1)
        self._is_locked = True

    def _release(self):
        if self._is_locked:
            os.close(self.fd)
            os.unlink(self._lockfile)
            self._is_locked = False

    def __enter__(self):
        if not self._is_locked:
            self._acquire()
        return self

    def __exit__(self, type, value, traceback):
        if self._is_locked:
            self._release()

    def __del__(self):
        self._release()
