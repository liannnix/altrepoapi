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

import re
from collections import namedtuple

from altrepo_api.api.base import APIWorker
from ..sql import sql


def parse_license_tokens(
    licenses_str: str, aliases: dict[str, str], spdx_ids: set[str]
) -> dict[str, str]:
    tokens: dict[str, str] = {}
    license_match = re.compile(r"[A-Za-z0-9\-\.\+]+")
    tokens_ = license_match.findall(licenses_str)
    all_valid_tokens = spdx_ids | aliases.keys()
    # skip if license string not starts with valid token
    if tokens_ and tokens_[0] not in all_valid_tokens:
        return tokens
    # remove unmatched tokens
    tokens_ = [t for t in tokens_ if t in all_valid_tokens]
    # # replace license aliases with actual SPDX license names
    tokens = {t: aliases.get(t, t) for t in tokens_}

    return tokens


class LicenseParser(APIWorker):
    """Retrieves license tokens from input string and database."""

    def __init__(
        self,
        connection,
        license_str: str,
    ):
        self.conn = connection
        self.sql = sql
        self.license = license_str
        self.tokens = {}
        super().__init__()

    def parse_license(self):
        # get license aliases from database
        response = self.send_sql_request(self.sql.get_aliases)
        if not self.sql_status:
            return
        aliases = {}
        if response:
            for el in response:  # type: ignore
                aliases[el[0]] = el[1]
        # get SPDX license names
        response = self.send_sql_request(self.sql.get_spdx_ids)
        if not self.sql_status:
            return
        spdx_ids = set()
        if response:
            spdx_ids = {el[0] for el in response}  # type: ignore
        # build found valid license tokens dictionary
        self.tokens = parse_license_tokens(self.license, aliases, spdx_ids)
        self.status = True


class LicenseTokens(APIWorker):
    """Parses string for valid license tokens."""

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def get(self):
        lp = LicenseParser(connection=self.conn, license_str=self.args["license"])
        lp.parse_license()
        if lp.status:
            if not lp.tokens:
                return self.store_error(
                    {
                        "message": "No valid license tokens found",
                        "args": self.args,
                    }
                )
            res = {
                "request_args": self.args,
                "length": len(lp.tokens),
                "tokens": [{"token": k, "license": v} for k, v in lp.tokens.items()],
            }
            return res, 200
        else:
            return lp.error


class LicenseInfo(APIWorker):
    """Retrievse license information from database."""

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def get(self):
        lp = LicenseParser(connection=self.conn, license_str=self.args["license"])
        lp.parse_license()
        if lp.status:
            if not lp.tokens:
                return self.store_error(
                    {
                        "message": "No valid license tokens found",
                        "args": self.args,
                    }
                )

            spdx_id = list(lp.tokens.values())[0]
            response = self.send_sql_request(
                self.sql.get_license_info.format(id=spdx_id)
            )
            if not self.sql_status:
                return self.error
            if not response:
                return self.store_error(
                    {"message": "No data not found in database", "args": self.args}
                )

            LicenseInfo = namedtuple(
                "LicenseInfo", ["id", "name", "text", "header", "urls", "type"]
            )
            license_info = LicenseInfo(*response[0])  # type: ignore

            res = {
                "request_args": self.args,
                "id": license_info.id,
                "name": license_info.name,
                "text": license_info.text,
                "type": license_info.type,
                "urls": license_info.urls,
                "header": license_info.header if license_info.type == "license" else "",
                "comment": (
                    license_info.header if license_info.type == "exception" else ""
                ),
            }
            return res, 200
        else:
            return lp.error
