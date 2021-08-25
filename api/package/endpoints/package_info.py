from utils import datetime_to_iso, tuplelist_to_dict, convert_to_dict, join_tuples

from api.base import APIWorker
from api.misc import lut
from database.package_sql import packagesql


class PackageInfo(APIWorker):
    """Retrieves package information by various arguments."""
    
    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = packagesql
        super().__init__()

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        self.validation_results = []

        if self.args["branch"] and self.args["branch"] not in lut.known_branches:
            self.validation_results.append(
                f"unknown package set name : {self.args['branch']}"
            )
            self.validation_results.append(
                f"allowed package set names are : {lut.known_branches}"
            )

        if self.args["arch"]:
            if self.args["arch"] not in lut.known_archs:
                self.validation_results.append(
                    f"unknown package arch : {self.args['arch']}"
                )
                self.validation_results.append(f"allowed archs are : {lut.known_archs}")

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
        self.conn.request_line = (request_line, {"branch": self.args["branch"]})
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        if not response:
            self._store_error(
                {
                    "message": f"No packages found in last packages for given parameters",
                    "args": self.args,
                },
                self.ll.INFO,
                404,
            )
            return self.error

        retval = convert_to_dict(["pkg_hash"] + output_params, response)

        if self.args["full"] and len(response) > 0:
            pkghashs = join_tuples(response)
            # changelogs
            self.conn.request_line = (
                self.sql.pkg_info_get_changelog,
                {"pkghshs": pkghashs},
            )
            status, response = self.conn.send_request()
            if not status:
                self._store_sql_error(response, self.ll.ERROR, 500)
                return self.error

            changelog_dict = {}
            # add empty dict for package changelogs
            for hsh in pkghashs:
                changelog_dict[hsh] = {}

            dict_ = tuplelist_to_dict(response, 1)
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
            self.conn.request_line = (
                self.sql.pkg_info_get_files,
                {"pkghshs": pkghashs},
            )
            status, response = self.conn.send_request()
            if status is False:
                self._store_sql_error(response, self.ll.ERROR, 500)
                return self.error

            files_dict = tuplelist_to_dict(response, 1)

            # add empty list if package has no files
            for hsh in pkghashs:
                if hsh not in files_dict:
                    files_dict[hsh] = []

            # depends
            self.conn.request_line = (
                self.sql.pkg_info_get_depends,
                {"pkghshs": pkghashs},
            )
            status, response = self.conn.send_request()
            if status is False:
                self._store_sql_error(response, self.ll.ERROR, 500)
                return self.error

            depends_dict = tuplelist_to_dict(response, 2)

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
