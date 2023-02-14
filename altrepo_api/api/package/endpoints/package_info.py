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

from altrepo_api.utils import (
    datetime_to_iso,
    tuplelist_to_dict,
    convert_to_dict,
    join_tuples,
)

from altrepo_api.api.base import APIWorker
from altrepo_api.api.misc import lut
from ..sql import sql


class PackageInfo(APIWorker):
    """Retrieves package information by various arguments."""

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        self.validation_results = []

        param_keys = (
            "sha1",
            "name",
            "version",
            "release",
            "arch",
            "disttag",
            "packager",
            "packager_email",
        )
        is_set = False
        for k in param_keys:
            if self.args[k] is not None:
                is_set = True
                break
        if not is_set:
            self.validation_results.append(
                f"at least one of request parameters should be specified: {param_keys}"
            )

        if self.validation_results != []:
            return False
        else:
            return True

    def get(self):
        output_params = [
            "pkg_cs",
            "pkg_packager",
            "pkg_packager_email",
            "pkg_name",
            "pkg_arch",
            "pkg_version",
            "pkg_release",
            "pkg_epoch",
            "pkg_disttag",
            "pkg_sourcepackage",
            "pkg_sourcerpm",
            "pkg_filename",
        ]
        if self.args["full"]:
            output_params = lut.package_params
        # convert input args into sql reqest 'WHERE' conditions
        params_values = []
        input_params = {
            "sha1": "pkg_cs",
            "name": "pkg_name",
            "version": "pkg_version",
            "release": "pkg_release",
            "arch": "pkg_arch",
            "disttag": "pkg_disttag",
            "packager": "pkg_packager",
            "packager_email": "pkg_packager_email",
        }
        for k, v in input_params.items():
            if self.args[k] is not None:
                params_values.append(f"{v} = '{self.args[k]}'")
        if self.args["source"]:
            params_values.append("pkg_sourcepackage = 1")
        else:
            params_values.append("pkg_sourcepackage = 0")

        request_line = self.sql.pkg_info_get_pkgs_template.format(
            p_params=", ".join(output_params),
            p_values=" AND ".join(params_values),
            branch="{}",
        )

        if self.args["branch"]:
            request_line = request_line.format("AND pkgset_name = %(branch)s")
        else:
            request_line = request_line.format("")

        # TODO: deal with 'Out of memory' from SQL server with all_packages - last_packages is OK
        response = self.send_sql_request(
            (request_line, {"branch": self.args["branch"]})
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {
                    "message": "No packages found in last packages for given parameters",
                    "args": self.args,
                }
            )

        retval = convert_to_dict(["pkg_hash"] + output_params, response)  # type: ignore

        if self.args["full"] and len(response) > 0:  # type: ignore
            pkghashs = join_tuples(response)  # type: ignore
            # changelogs
            response = self.send_sql_request(
                (
                    self.sql.pkg_info_get_changelog,
                    {"pkghshs": pkghashs},
                )
            )
            if not self.sql_status:
                return self.error

            changelog_dict = {}
            # add empty dict for package changelogs
            for hsh in pkghashs:
                changelog_dict[hsh] = {}

            dict_ = tuplelist_to_dict(response, 1)  # type: ignore
            for pkghash, changelog in dict_.items():
                i = 0
                for v in changelog:
                    changelog_dict[pkghash][i] = {}
                    changelog_dict[pkghash][i]["date"] = datetime_to_iso(v[0])
                    changelog_dict[pkghash][i]["name"] = v[1]
                    changelog_dict[pkghash][i]["evr"] = v[2]
                    changelog_dict[pkghash][i]["message"] = v[3]
                    i += 1

            # files
            response = self.send_sql_request(
                (
                    self.sql.pkg_info_get_files,
                    {"pkghshs": pkghashs},
                )
            )
            if not self.sql_status:
                return self.error

            files_dict = tuplelist_to_dict(response, 1)  # type: ignore

            # add empty list if package has no files
            for hsh in pkghashs:
                if hsh not in files_dict:
                    files_dict[hsh] = []

            # depends
            response = self.send_sql_request(
                (
                    self.sql.pkg_info_get_depends,
                    {"pkghshs": pkghashs},
                )
            )
            if not self.sql_status:
                return self.error

            depends_dict = tuplelist_to_dict(response, 2)  # type: ignore

            depends_struct = {}
            for pkg in depends_dict:
                depend_ls = depends_dict[pkg]

                depends_struct[pkg] = {}

                for i in range(0, len(depend_ls), 2):
                    if depend_ls[i] not in depends_struct[pkg]:
                        depends_struct[pkg][depend_ls[i]] = []

                    depends_struct[pkg][depend_ls[i]].append(depend_ls[i + 1])

            for elem in retval:
                pkghash = retval[elem]["pkg_hash"]
                # add changelog to result structure
                retval[elem]["changelog"] = [
                    x for x in changelog_dict[pkghash].values()
                ]
                # add files to result structure
                retval[elem]["files"] = files_dict[pkghash]
                # add depends to result structure
                retval[elem]["depends"] = {}
                for dep in depends_struct[pkghash]:
                    retval[elem]["depends"][dep] = depends_struct[pkghash][dep]

        # remove pkghash from result
        for value in retval.values():
            value.pop("pkg_hash", None)
            value.pop("pkg_srcrpm_hash", None)

        res = {
            "request_args": self.args,
            "length": len(retval),
            "packages": [x for x in retval.values()],
        }

        return res, 200
