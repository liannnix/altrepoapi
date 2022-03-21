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

import datetime
from io import BytesIO
from collections import namedtuple

from altrepo_api.api.base import APIWorker
from ..sql import sql


PO_FILE_NAME_BASE = "packages.po"
PO_HEADER = """
# SOME DESCRIPTIVE TITLE
# Copyright (C) YEAR Free Software Foundation, Inc.
# This file is distributed under the same license as the PACKAGE package.
# FIRST AUTHOR <EMAIL@ADDRESS>, YEAR.
# 
#, fuzzy
msgid ""
msgstr ""
"Project-Id-Version: PACKAGE VERSION\\n"
"POT-Creation-Date: {created_date}+0300\\n"
"PO-Revision-Date: YEAR-MO-DA HO:MI+ZONE\\n"
"Last-Translator: FULL NAME <EMAIL@ADDRESS>\\n"
"Language-Team: LANGUAGE <LL@li.org>\\n"
"MIME-Version: 1.0\\n"
"Content-Type: text/plain; charset=UTF-8\\n"
"Content-Transfer-Encoding: 8bit\\n"

"""

PkgInfo = namedtuple(
    "PkgInfo", ["name", "url", "summary", "description", "src_pkg_name"]
)


def format_po_file(packages: list[PkgInfo], uniq_only: bool = False) -> BytesIO:
    result = BytesIO()

    uniq_summary = set()
    uniq_description = set()

    def format_message(msg):
        res = ""
        if "\n" in msg:
            lines = msg.split("\n")
            res += 'msgid ""\n'
            for line in lines:
                res += f'"{line}\\n"\n'
        else:
            res = f'msgid "{msg}"\n'
        return res

    # write PO-file header
    header = PO_HEADER.format(created_date=datetime.datetime.now().strftime('%Y-%m-%d %H:%m'))
    result.write(header.encode())

    for pkg in packages:
        str_ = ""
        if pkg.summary not in uniq_summary:
            str_ += f"#: {pkg.name}\n"
            str_ += f"#. homepage: {pkg.url}\n"
            str_ += "#. summary\n"
            str_ += format_message(pkg.summary)
            str_ += "msgstr \n\n"
            if uniq_only:
                uniq_summary.add(pkg.summary)
        if pkg.description not in uniq_description:
            str_ += f"#: {pkg.name}\n"
            str_ += f"#. homepage: {pkg.url}\n"
            str_ += "#. description\n"
            str_ += format_message(pkg.description)
            str_ += "msgstr \n\n"
            if uniq_only:
                uniq_description.add(pkg.description)
        if str_ != "":
            result.write(str_.encode())
    return result


class TranslationExport(APIWorker):
    """Retrieves a PO file with package's summary and description."""

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def get(self):
        branches = tuple(self.args["branches"])

        self.conn.request_line = self.sql.get_packages_descriptions.format(
            branches=branches
        )
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        if not response:
            self._store_error(
                {
                    "message": f"No data found in DB",
                    "args": self.args,
                },
                self.ll.INFO,
                404,
            )
            return self.error

        po_file = format_po_file(
            sorted([PkgInfo(*el) for el in response], key=lambda pkg: pkg.src_pkg_name), # type: ignore
            uniq_only=True,
        )
        po_file_name  = PO_FILE_NAME_BASE

        return {"file": po_file, "file_name": po_file_name}, 200
