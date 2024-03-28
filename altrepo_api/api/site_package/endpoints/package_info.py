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

from collections import namedtuple
from typing import Any, NamedTuple

from altrepo_api.utils import (
    datetime_to_iso,
    tuplelist_to_dict,
    sort_branches,
    get_nickname_from_packager,
    dp_flags_decode,
)

from altrepo_api.api.base import APIWorker
from altrepo_api.api.misc import lut
from ..sql import sql
from altrepo_api.api.license.endpoints.license import LicenseParser
from .common import FindBuildTaskMixixn, SQLRequestError, NoDataFoundInDB


MAX_CHLOG_LENGTH = 100


class PackageInfo(FindBuildTaskMixixn, APIWorker):
    """Retrieves package info from DB."""

    def __init__(self, connection, pkghash, **kwargs):
        self.pkghash = pkghash
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        self.lut = lut
        super().__init__()

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        self.validation_results = []

        chlog_length = self.args["changelog_last"]

        if chlog_length < 1 or chlog_length > MAX_CHLOG_LENGTH:
            self.validation_results.append(
                f"changelog history length should be in range 1 to {MAX_CHLOG_LENGTH}"
            )

        return self.validation_results == []

    class PackageMeta(NamedTuple):
        name: str
        version: str
        release: str
        arch: str
        epoch: int
        buildtime: int
        url: str
        license: str
        summary: str
        description: str
        packager: str
        packager_nickname: str
        category: str

    def maintainers(self) -> list[str]:
        maintainers = []
        response = self.send_sql_request(
            self.sql.get_pkg_maintainers.format(pkghash=self.pkghash)
        )
        if not self.sql_status:
            raise SQLRequestError

        for el in response[0][0]:
            if "altlinux" in el:
                nickname = get_nickname_from_packager(el)
                if nickname not in maintainers:
                    maintainers.append(nickname)

        return maintainers

    def acl(self) -> list[str]:
        response = self.send_sql_request(
            self.sql.get_pkg_acl.format(name=self.pkg_info.name, branch=self.branch)
        )
        if not self.sql_status:
            raise SQLRequestError

        return response[0][0] if response else []

    def dependencies(self) -> list[dict[str, Any]]:
        PkgDeps = namedtuple("PkgDeps", ["name", "version", "flag"])
        dependencies = []

        if self.is_src:
            response = self.send_sql_request(
                self.sql.get_pkg_dependencies.format(pkghash=self.pkghash)
            )
            if not self.sql_status:
                raise SQLRequestError

            dependencies = [PkgDeps(*el)._asdict() for el in response]

            # change numeric flag on text
            for el in dependencies:
                el["flag_decoded"] = dp_flags_decode(el["flag"], lut.rpmsense_flags)
                el["type"] = "require"

        return dependencies

    def changelog(self) -> list[dict[str, Any]]:
        Changelog = namedtuple("Changelog", ["date", "name", "nick", "evr", "message"])

        response = self.send_sql_request(
            (
                self.sql.get_pkg_changelog,
                {"pkghash": self.pkghash, "limit": self.chlog_length},
            )
        )
        if not self.sql_status:
            raise SQLRequestError
        if not response:
            raise NoDataFoundInDB

        return [Changelog(datetime_to_iso(el[1]), *el[2:])._asdict() for el in response]

    def beehive_status(self) -> list[dict[str, Any]]:
        BeehiveStatus = namedtuple(
            "BeehiveStatus",
            ["arch", "status", "build_time", "updated", "ftbfs_since"],
        )

        if self.branch not in lut.known_beehive_branches:
            # return empty result list if branch not in beehive branches
            return []

        # get last beehive errors by package hash
        response = self.send_sql_request(
            self.sql.get_last_bh_rebuild_status_by_hsh.format(
                branch=self.branch, pkghash=self.pkghash
            )
        )
        if not self.sql_status:
            raise SQLRequestError

        bh_status = [BeehiveStatus(*el)._asdict() for el in response]

        for bh in bh_status:
            epoch_ = self.pkg_info.epoch
            if epoch_ == 0:
                epoch_version = self.pkg_info.version
            else:
                epoch_version = str(epoch_) + ":" + self.pkg_info.version

            url = "/".join(
                (
                    lut.beehive_base,
                    "logs",
                    "Sisyphus" if self.branch == "sisyphus" else self.branch,
                    bh["arch"],
                    "archive",
                    bh["updated"].strftime("%Y/%m%d"),
                    "error",
                    "-".join(
                        (self.pkg_info.name, epoch_version, self.pkg_info.release)
                    ),
                )
            )
            if bh["status"] == "error":
                bh["url"] = url
            else:
                bh["url"] = ""
            bh["updated"] = datetime_to_iso(bh["updated"])
            bh["ftbfs_since"] = datetime_to_iso(bh["ftbfs_since"])

        return bh_status

    def license_tokens(self) -> list[dict[str, Any]]:
        lp = LicenseParser(connection=self.conn, license_str=self.pkg_info.license)
        lp.parse_license()

        if not lp.status:
            raise SQLRequestError("Failed to get license tokens", error=lp.error)
        if not lp.tokens:
            return []
        return [{"token": k, "license": v} for k, v in lp.tokens.items()]

    def new_package_version(self) -> dict[str, Any]:
        ver_in_repo = None

        PackageVR = namedtuple("PackageVR", ["version", "release"])

        response = self.send_sql_request(
            self.sql.get_current_pkg_version.format(
                name=self.pkg_info.name, branch=self.branch, is_src=self.is_src
            )
        )
        if not self.sql_status:
            raise SQLRequestError

        if response:
            ver_in_repo = PackageVR(*response[0])

        if ver_in_repo is not None:
            NewPackageVersion = namedtuple(
                "NewPackageVersion",
                ["task_id", "date", "pkghash", "version", "release"],
            )
            pkg_arch = (
                f"AND pkg_arch = '{self.pkg_info.arch}'" if self.is_src == 0 else ""
            )
            pkg_src_or_bin = f"AND pkg_sourcepackage = {self.is_src}"
            response = self.send_sql_request(
                self.sql.get_new_pkg_version.format(
                    pkg_name=self.pkg_info.name,
                    branch=self.branch,
                    source=pkg_src_or_bin,
                    arch=pkg_arch,
                    ver=ver_in_repo.version,
                    rel=ver_in_repo.release,
                    cur_ver=self.pkg_info.version,
                    cur_rel=self.pkg_info.release,
                ),
            )
            if not self.sql_status:
                raise SQLRequestError
            if response:
                return NewPackageVersion(*response[0])._asdict()

        return {}

    def get(self):
        self.branch = self.args["branch"]
        self.chlog_length = self.args["changelog_last"]
        self.is_src = {"source": 1, "binary": 0}[self.args["package_type"]]

        # get package info
        pkg_src_or_bin = f"AND pkg_sourcepackage = {self.is_src}"

        response = self.send_sql_request(
            self.sql.get_pkg_info.format(pkghash=self.pkghash, source=pkg_src_or_bin)
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {
                    "message": f"No data found in DB for package {self.pkghash}",
                    "args": self.args,
                }
            )

        self.pkg_info = self.PackageMeta(*response[0])

        # get package build task
        pkg_task = 0
        pkg_tasks = []
        pkg_subtask = 0
        pkg_task_date = None
        gear_link = ""

        try:
            if self.branch not in lut.taskless_branches:
                # get package build tasks by hash
                (
                    pkg_task,
                    pkg_subtask,
                    pkg_task_date,
                    gear_link,
                    pkg_tasks,
                ) = self.find_and_parse_build_task()
            # get package maintainers from changelog
            pkg_maintainers = self.maintainers()
            # get package ACLs
            pkg_acl = self.acl()
            # get package newest versions from DONE tasks
            new_evr = self.new_package_version()
            # get package dependencies
            pkg_dependencies = self.dependencies()
            # get package changelog
            changelog_list = self.changelog()
            # get package beehive rebuild status
            bh_status = self.beehive_status()
            # get package license tokens
            license_tokens = self.license_tokens()
        except SQLRequestError as e:
            if e.error:
                return e.error
            return self.error
        except NoDataFoundInDB:
            return self.store_error(
                {
                    "message": f"No data found in DB for package {self.pkghash}",
                    "args": self.args,
                }
            )

        # get provided binary and source packages
        package_archs = {}
        if not (pkg_task and pkg_subtask):
            if self.is_src:
                response = self.send_sql_request(
                    self.sql.get_binary_pkgs_from_last_pkgs.format(
                        pkghash=self.pkghash, branch=self.branch, bin_pkg_clause=""
                    )
                )
                if not response:
                    response = self.send_sql_request(
                        self.sql.get_binary_pkgs.format(
                            pkghash=self.pkghash, branch=self.branch
                        )
                    )
            else:
                response = self.send_sql_request(
                    self.sql.get_source_pkgs.format(pkghash=self.pkghash)
                )
        else:
            # (bug: #45195)
            if self.is_src:
                response = self.send_sql_request(
                    self.sql.get_binaries_from_task.format(
                        taskid=pkg_task, subtaskid=pkg_subtask, changed=pkg_task_date
                    )
                )
            else:
                response = self.send_sql_request(
                    self.sql.get_source_pkgs.format(pkghash=self.pkghash)
                )

        if not self.sql_status:
            return self.error

        if response:
            if self.is_src:
                # (bug #41537) some binaries built from old source package
                # in not 'DONE' tasks leads to misleading build time
                self.pkg_info = self.pkg_info._replace(buildtime=response[0][2])

                # find appropriate hash for 'noarch' packages using build task
                # and architecture precedence
                _bin_pkgs_arch_hshs_from_task = {}

                if pkg_task != 0 and any(
                    [["noarch" == p[0] for el in response for p in el[1]]]
                ):
                    # get task iterations binary packages hashes by arch
                    _response = self.send_sql_request(
                        self.sql.get_task_bin_hshs_by_src_hsh.format(
                            pkghash=self.pkghash, task_id=pkg_task
                        )
                    )
                    if not self.sql_status:
                        return self.error
                    if not _response:
                        return self.store_error(
                            {
                                "message": f"No task data found for ({pkg_task})",
                                "args": self.args,
                            }
                        )
                    # dict(arch, set(hash))
                    _bin_pkgs_arch_hshs_from_task = {
                        el[2]: set(el[3]) for el in _response
                    }

                for elem in response:
                    # dict(arch: hash)
                    _pkgs_arch_hsh_dict = {el[0]: str(el[1]) for el in elem[1]}
                    # list[(arch, hash), ...]
                    _pkgs_arch_hsh_list = [(el[0], el[1]) for el in elem[1]]
                    # handle multiple noarch packages here if any
                    if (
                        _bin_pkgs_arch_hshs_from_task
                        and "noarch" in _pkgs_arch_hsh_dict
                        and len(_pkgs_arch_hsh_list) > 1
                    ):
                        # build archs list with 'x86_64' and 'i586' precedence
                        _archs = ["x86_64", "i586"]
                        _archs += [
                            k for k in _bin_pkgs_arch_hshs_from_task if k not in _archs
                        ]
                        # find proper 'noarch' binary from build task
                        for _arch in _archs:
                            # skip if current arch not built in task
                            if _arch not in _bin_pkgs_arch_hshs_from_task:
                                continue
                            # find proper 'noarch' binary package hash
                            for pkg in _pkgs_arch_hsh_list:
                                if pkg[1] in _bin_pkgs_arch_hshs_from_task[_arch]:
                                    package_archs[elem[0]] = {"noarch": str(pkg[1])}
                                    break
                            break
                    else:
                        package_archs[elem[0]] = _pkgs_arch_hsh_dict
            else:
                for elem in response:
                    package_archs[elem[0]] = {"src": str(elem[1])}

        res_package_archs = []
        for k, v in package_archs.items():
            tmp = {"name": k, "archs": [], "pkghash": []}
            for arch, hash in v.items():
                tmp["archs"].append(arch)
                tmp["pkghash"].append(str(hash))
            res_package_archs.append(tmp)

        # fix gear_link for binary packages
        if not self.is_src:
            pkgname_binary = self.pkg_info.name
            try:
                pkgname_source = list(package_archs.keys())[0]
                in_ = f"{pkgname_binary[0]}/{pkgname_binary}.git"
                out_ = f"{pkgname_source[0]}/{pkgname_source}.git"
                gear_link = gear_link.replace(in_, out_)
            except IndexError:
                pkgname_source = ""
                gear_link = ""

        res = {
            "pkghash": str(self.pkghash),
            "request_args": self.args,
            **self.pkg_info._asdict(),
            "task": pkg_task,
            "task_date": pkg_task_date if pkg_task_date is not None else "",
            "gear": gear_link,
            "tasks": pkg_tasks,
            "package_archs": res_package_archs,
            "changelog": changelog_list,
            "maintainers": pkg_maintainers,
            "acl": pkg_acl,
            "new_version": [new_evr] if new_evr else [],
            "beehive": bh_status,
            "dependencies": pkg_dependencies,
            "license_tokens": license_tokens,
        }

        return res, 200


class DeletedPackageInfo(APIWorker):
    """Retrieves information about deleted package."""

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        self.validation_results = []

        if self.args["package_type"] == "binary":
            if self.args["arch"] not in lut.known_archs:
                self.validation_results.append(
                    f"binary package arch should be in {lut.known_archs}"
                )

        if self.validation_results != []:
            return False
        else:
            return True

    def get(self):
        self.branch = self.args["branch"]
        self.name = self.args["name"]
        self.arch = self.args["arch"]
        source = 1 if self.args["package_type"] == "source" else 0

        if source:
            # get task info where source package was deleted
            request_line = self.sql.get_deleted_package_task_by_src.format(
                name=self.name, branch=self.branch
            )
        else:
            # get task info where source package of input binary was deleted
            request_line = self.sql.get_deleted_package_task_by_bin.format(
                name=self.name, branch=self.branch
            )

        response = self.send_sql_request(request_line)
        if not self.sql_status:
            return self.error

        TaskMeta = namedtuple(
            "TaskMeta",
            ["task_id", "subtask_id", "task_changed", "task_owner", "subtask_userid"],
        )

        delete_task_info = {}
        delete_task_info["task_message"] = ""

        if response:
            delete_task_info = TaskMeta(*response[0])._asdict()

            # task in wich source package was deleted found
            # get last package version info from branch
            if source:
                request_line = self.sql.get_srcpkg_hash_for_branch_on_date.format(
                    name=self.name,
                    branch=self.branch,
                    task_changed=delete_task_info["task_changed"],
                )
            else:
                request_line = self.sql.get_binpkg_hash_for_branch_on_date.format(
                    arch=self.arch,
                    name=self.name,
                    branch=self.branch,
                    task_changed=delete_task_info["task_changed"],
                )

            response = self.send_sql_request(request_line)
            if not self.sql_status:
                return self.error

            if response:
                pkg_hash = str(response[0][0])
                pkg_version = str(response[0][1])
                pkg_release = str(response[0][2])
            else:
                #  find if package were ever built before delete
                if source:
                    # get task info where source package was last built before delete
                    presel_sql = self.sql.preselect_last_build_task_by_src.format(
                        name=self.name
                    )
                else:
                    # get task info where source package of input binary was was last built before delete
                    presel_sql = self.sql.preselect_last_build_task_by_bin.format(
                        name=self.name, arch=self.arch
                    )

                response = self.send_sql_request(
                    self.sql.get_last_build_task_by_pkg.format(
                        preselect=presel_sql,
                        branch=self.branch,
                        task_changed=delete_task_info["task_changed"],
                    )
                )
                if not self.sql_status:
                    return self.error

                # nothing helped to find out package history
                if not response:
                    return self.store_error(
                        {
                            "message": f"No information about deleting package {self.name} from {self.branch} was found",
                            "args": self.args,
                        }
                    )

                pkg_hash = str(response[0][1])
                pkg_version = str(response[0][2])
                pkg_release = str(response[0][3])
        else:
            # try to find task info from 'lv_branch_deleted_packages'
            response = self.send_sql_request(
                self.sql.get_delete_task_from_branch_history.format(
                    name=self.name, branch=self.branch
                )
            )
            if not self.sql_status:
                return self.error
            if response:
                delete_task_info = TaskMeta(*response[0][:-1])._asdict()
                pkg_hash = response[0][-1]
                if delete_task_info["subtask_id"] == 0:
                    delete_task_info["subtask_id"] = -1
            else:
                # task in wich source package was deleted not found
                arch_ = ""
                if not source:
                    arch_ = f"with {self.arch} arch "

                return self.store_error(
                    {
                        "message": f"No information about deleting package {self.name} {arch_} from {self.branch} was found",
                        "args": self.args,
                    }
                )

            # get package info by hash
            where_clause = f"{pkg_hash} AND pkg_sourcepackage = {source}"
            if not source:
                where_clause += f" AND pkg_arch = '{self.arch}'"

            response = self.send_sql_request(
                self.sql.get_package_nvr_by_hash.format(pkghash=where_clause)
            )
            if not self.sql_status:
                return self.error
            if not response:
                return self.store_error(
                    {
                        "message": f"No information about deleting package {self.name} from {self.branch} was found",
                        "args": self.args,
                    }
                )
            pkg_version, pkg_release = response[0][2], response[0][3]

        # get task message
        response = self.send_sql_request(
            self.sql.get_delete_task_message.format(
                task_id=delete_task_info["task_id"],
                task_changed=delete_task_info["task_changed"],
            )
        )
        if not self.sql_status:
            return self.error

        if response:
            delete_task_info["task_message"] = response[0][0]

        delete_task_info["task_changed"] = datetime_to_iso(
            delete_task_info["task_changed"]
        )

        res = {
            "package": self.name,
            "branch": self.branch,
            "hash": pkg_hash,
            "version": pkg_version,
            "release": pkg_release,
            **delete_task_info,
        }

        return res, 200


class PackagesBinaryListInfo(APIWorker):
    """Retrieves all binary package architecture."""

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        return True

    def get(self):
        self.branch = self.args["branch"]
        self.name = self.args["name"]

        response = self.send_sql_request(
            self.sql.get_pkgs_binary_list.format(branch=self.branch, name=self.name)
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {
                    "message": "No data found",
                    "args": self.args,
                }
            )

        PkgMeta = namedtuple(
            "PkgMeta",
            ["hash", "name", "version", "release", "arch"],
        )

        retval = [PkgMeta(*el)._asdict() for el in response]

        # get package versions
        pkg_versions = []

        response = self.send_sql_request(
            self.sql.get_pkg_binary_list_versions.format(name=retval[0]["name"])
        )
        if not self.sql_status:
            return self.error

        # sort package versions by branch
        pkg_branches = sort_branches([el[0] for el in response])
        pkg_versions = tuplelist_to_dict(response, 3)

        # XXX: workaround for multiple versions of returned for certain branch
        PkgVersions = namedtuple("PkgVersions", ["branch", "version", "release"])
        pkg_versions = [
            PkgVersions(*(b, *pkg_versions[b][-3:]))._asdict() for b in pkg_branches
        ]

        res = {
            "request_args": self.args,
            "length": len(retval),
            "packages": retval,
            "versions": pkg_versions,
        }

        return res, 200


class PackageNVRByHash(APIWorker):
    """Retrieves package NVR and type from DB."""

    def __init__(self, connection, pkghash, **kwargs):
        self.pkghash = pkghash
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def get(self):
        response = self.send_sql_request(
            self.sql.get_package_nvr_by_hash.format(pkghash=self.pkghash)
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {
                    "message": f"No packages found in DB with hash {self.pkghash}",
                    "args": self.args,
                }
            )

        PkgInfo = namedtuple(
            "PkgInfo", ["hash", "name", "version", "release", "is_source"]
        )

        pkg_info = PkgInfo(*response[0])

        # check if name from args matches with name from DB
        if self.args["name"] is not None and self.args["name"] != pkg_info.name:
            return self.store_error(
                {
                    "message": "Package name mismatching",
                    "args": self.args,
                }
            )

        res = {
            "request_args": self.args,
            "hash": str(pkg_info.hash),
            "name": pkg_info.name,
            "version": pkg_info.version,
            "release": pkg_info.release,
            "is_source": bool(pkg_info.is_source),
        }

        return res, 200


class PackageNameFromRepology(APIWorker):
    """Retrieves source package name from repology."""

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        self.validation_results = []

        if (
            self.args["branch"] == ""
            or self.args["branch"] not in lut.repology_export_branches
        ):
            self.validation_results.append(
                f"unknown package set name : {self.args['branch']}"
            )
            self.validation_results.append(
                f"allowed package set names are : {lut.repology_export_branches}"
            )

        if self.validation_results != []:
            return False
        else:
            return True

    def get(self):
        branch = lut.repology_branch_map[self.args["branch"]]
        pkg_name = self.args["name"]

        response = self.send_sql_request(
            self.sql.get_converted_pkg_name.format(branch=branch, pkg_name=pkg_name)
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {
                    "message": f"No packages found in DB with name {pkg_name}",
                    "args": self.args,
                }
            )

        PkgNameRepology = namedtuple("PkgNameRepology", ["name", "repo"])

        res = {"request_args": self.args, **PkgNameRepology(*response[0])._asdict()}

        return res, 200


class BriefPackageInfo(APIWorker):
    def __init__(self, connection, pkghash, **kwargs):
        self.pkghash = pkghash
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def get(self):
        response = self.send_sql_request(
            self.sql.get_brief_pkg_info.format(pkghash=self.pkghash)
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {
                    "message": (
                        f"No information was found in the database "
                        f"about the package with hash {self.pkghash}."
                    ),
                    "args": self.args,
                }
            )
        PkgInfoMeta = namedtuple(
            "PkgInfoMeta",
            ["name", "version", "release", "arch", "type", "summary"],
        )
        return PkgInfoMeta(*response[0])._asdict(), 200
