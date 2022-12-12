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

from collections import namedtuple

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


class PackageInfo(APIWorker):
    """Retrieves package info from DB."""

    def __init__(self, connection, pkghash, **kwargs):
        self.pkghash = pkghash
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        self.validation_results = []

        if self.args["changelog_last"] < 1:
            self.validation_results.append(
                "Changelog history length should be not less than 1"
            )

        if self.validation_results != []:
            return False
        else:
            return True

    @staticmethod
    def _parse_task_gear(pkgname, subtask, git_base_url):
        """Builds link to Git repository based on information from subtask.

        Args:
            pkgname (str): source package name
            subtask (dict): subtask information
            git_base_url (str): Git repository base URL

        Returns:
            str: link to Git repositroy
        """

        def delete_epoch(evr):
            #  delete epoch from evr
            if ":" in evr:
                return evr.split(":")[-1]
            return evr

        link_ = ""
        if subtask["type"] == "copy":
            # 'copy' always has only 'subtask_package'
            link_ = pkgname
        elif subtask["type"] == "delete" and subtask["srpm_name"] != "":
            # XXX: bug workaround for girar changes @ e74d8067009d
            link_ = f"{git_base_url}/srpms/{pkgname[0]}/{pkgname}.git"
            if subtask["srpm_evr"] != "":
                link_ += f"?a=tree;hb={delete_epoch(subtask['srpm_evr'])}"
        elif subtask["type"] == "delete":
            # 'delete' return only package name
            link_ = pkgname
        elif subtask["dir"] != "" or subtask["type"] == "gear":
            # 'gear' and 'rebuild' + 'unknown' with gears
            link_ = f"{git_base_url}/gears/{pkgname[0]}/{pkgname}.git"
            if subtask["tag_id"] != "":
                link_ += f"?a=tree;hb={subtask['tag_id']}"
        elif subtask["srpm_name"] != "" or subtask["type"] == "srpm":
            # 'srpm' and 'rebuild' + 'unknown' with srpm
            link_ = f"{git_base_url}/srpms/{pkgname[0]}/{pkgname}.git"
            if subtask["srpm_evr"] != "":
                link_ += f"?a=tree;hb={delete_epoch(subtask['srpm_evr'])}"
        return link_

    def get(self):
        self.branch = self.args["branch"]
        self.chlog_length = self.args["changelog_last"]
        self.pkg_type = self.args["package_type"]

        pkg_type_to_sql = {"source": 1, "binary": 0}
        source = pkg_type_to_sql[self.pkg_type]

        # get package info
        pkg_src_or_bin = f"AND pkg_sourcepackage = {source}"

        response = self.send_sql_request(
            self.sql.get_pkg_info.format(pkghash=self.pkghash, source=pkg_src_or_bin)
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {
                    "message": f"No packages found in last packages with hash {self.pkghash}",
                    "args": self.args,
                }
            )

        PkgMeta = namedtuple(
            "PkgMeta",
            [
                "name",
                "version",
                "release",
                "arch",
                "epoch",
                "buildtime",
                "url",
                "license",
                "summary",
                "description",
                "packager",
                "packager_nickname",
                "category",
            ],
        )

        pkg_info = PkgMeta(*response[0])._asdict()

        # get package task
        pkg_task = 0
        pkg_tasks = []
        pkg_task_date = None
        gear_link = ""

        SubtaskMeta = namedtuple(
            "SubtaskMeta",
            [
                "repo",
                "id",
                "sub_id",
                "type",
                "dir",
                "tag_id",
                "srpm_name",
                "srpm_evr",
                "changed",
            ],
        )

        # clear pkg_tasks for taskless branches
        if self.branch in lut.taskless_branches:
            pkg_task = 0
            pkg_tasks = []
            pkg_task_date = None
        else:
            response = self.send_sql_request(
                self.sql.get_task_gears_by_hash.format(pkghash=self.pkghash)
            )
            if not self.sql_status:
                return self.error

            if response:
                for task in [SubtaskMeta(*el)._asdict() for el in response]:
                    if task["repo"] == self.branch:
                        pkg_task = task["id"]
                        pkg_task_date = datetime_to_iso(task["changed"])
                        if task["type"] != "copy":
                            gear_link = self._parse_task_gear(
                                pkg_info["name"], task, lut.gitalt_base
                            )
                            pkg_tasks.append(
                                {"type": "build", "id": pkg_task, "date": pkg_task_date}
                            )
                            break
                        else:
                            pkg_tasks.append(
                                {"type": "copy", "id": pkg_task, "date": pkg_task_date}
                            )
                    else:
                        if task["type"] != "copy":
                            pkg_task = task["id"]
                            pkg_task_date = datetime_to_iso(task["changed"])
                            gear_link = self._parse_task_gear(
                                pkg_info["name"], task, lut.gitalt_base
                            )
                            pkg_tasks.append(
                                {"type": "build", "id": pkg_task, "date": pkg_task_date}
                            )
                            break

        # get package maintainers from changelog
        pkg_maintainers = []

        response = self.send_sql_request(
            self.sql.get_pkg_maintainers.format(pkghash=self.pkghash)
        )
        if not self.sql_status:
            return self.error

        for el in response[0][0]:
            if "altlinux" in el:
                nickname = get_nickname_from_packager(el)
                if nickname not in pkg_maintainers:
                    pkg_maintainers.append(nickname)

        # get package ACLs
        pkg_acl = []

        response = self.send_sql_request(
            self.sql.get_pkg_acl.format(name=pkg_info["name"], branch=self.branch)
        )
        if not self.sql_status:
            return self.error

        if response:
            pkg_acl = response[0][0]

        # get package versions
        pkg_versions = []

        if source:
            request_line = self.sql.get_pkg_versions.format(name=pkg_info["name"])
        else:
            request_line = self.sql.get_pkg_binary_versions.format(
                name=pkg_info["name"], arch=pkg_info["arch"]
            )

        response = self.send_sql_request(request_line)
        if not self.sql_status:
            return self.error

        # sort package versions by branch
        pkg_branches = sort_branches([el[0] for el in response])
        pkg_versions = tuplelist_to_dict(response, 3)

        # XXX: workaround for multiple versions of returned for certain branch
        PkgVersions = namedtuple(
            "PkgVersions", ["branch", "version", "release", "pkghash"]
        )

        pkg_versions = [
            PkgVersions(*(b, *pkg_versions[b][-3:]))._asdict() for b in pkg_branches
        ]

        # get package dependencies
        pkg_dependencies = []
        if source == 1:
            response = self.send_sql_request(
                self.sql.get_pkg_dependencies.format(pkghash=self.pkghash)
            )
            if not self.sql_status:
                return self.error

            PkgDependencies = namedtuple("PkgDependencies", ["name", "version", "flag"])
            pkg_dependencies = [PkgDependencies(*el)._asdict() for el in response]

            # change numeric flag on text
            for el in pkg_dependencies:
                el["flag_decoded"] = dp_flags_decode(el["flag"], lut.rpmsense_flags)

        # get provided binary and source packages
        package_archs = {}
        if source:
            request_line = self.sql.get_binary_pkgs.format(
                pkghash=self.pkghash, branch=self.branch
            )
        else:
            request_line = self.sql.get_source_pkgs.format(pkghash=self.pkghash)

        response = self.send_sql_request(request_line)
        if not self.sql_status:
            return self.error

        if response:
            if source:
                pkg_info["buildtime"] = response[0][2]  # type: ignore
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

        # get package changelog
        response = self.send_sql_request(
            (
                self.sql.get_pkg_changelog,
                {"pkghash": self.pkghash, "limit": self.chlog_length},
            )
        )
        if not self.sql_status:
            return self.error
        if not response:
            return self.store_error(
                {
                    "message": f"No packages found in last packages with hash {self.pkghash}",
                    "args": self.args,
                }
            )

        Changelog = namedtuple("Changelog", ["date", "name", "nick", "evr", "message"])

        changelog_list = [
            Changelog(datetime_to_iso(el[1]), *el[2:])._asdict() for el in response
        ]

        # get package beehive rebuild status
        if self.branch not in lut.known_beehive_branches:
            # return empty result list if branch not in beehive branches
            bh_status = []
        else:
            # get last beehive errors by package hash
            response = self.send_sql_request(
                (
                    self.sql.get_last_bh_rebuild_status_by_hsh,
                    {"pkghash": self.pkghash, "branch": self.branch},
                )
            )
            if not self.sql_status:
                return self.error

            BeehiveStatus = namedtuple(
                "BeehiveStatus",
                ["arch", "status", "build_time", "updated", "ftbfs_since"],
            )

            bh_status = [BeehiveStatus(*el)._asdict() for el in response]

            for bh in bh_status:
                epoch_ = pkg_info["epoch"]
                if epoch_ == 0:
                    epoch_version = pkg_info["version"]
                else:
                    epoch_version = str(epoch_) + ":" + pkg_info["version"]

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
                            (pkg_info["name"], epoch_version, pkg_info["release"])
                        ),
                    )
                )
                if bh["status"] == "error":
                    bh["url"] = url
                else:
                    bh["url"] = ""
                bh["updated"] = datetime_to_iso(bh["updated"])
                bh["ftbfs_since"] = datetime_to_iso(bh["ftbfs_since"])

        res_package_archs = []
        for k, v in package_archs.items():
            tmp = {"name": k, "archs": [], "pkghash": []}
            for arch, hash in v.items():
                tmp["archs"].append(arch)
                tmp["pkghash"].append(str(hash))
            res_package_archs.append(tmp)

        # get package license tokens
        license_tokens = []

        lp = LicenseParser(connection=self.conn, license_str=pkg_info["license"])
        lp.parse_license()

        if lp.status:
            if lp.tokens:
                license_tokens = [
                    {"token": k, "license": v} for k, v in lp.tokens.items()
                ]
        else:
            return lp.error

        # fix gear_link for binary packages
        if source == 0:
            pkgname_binary = pkg_info["name"]
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
            **pkg_info,
            "task": pkg_task,
            "task_date": pkg_task_date if pkg_task_date is not None else "",
            "gear": gear_link,
            "tasks": pkg_tasks,
            "package_archs": res_package_archs,
            "changelog": changelog_list,
            "maintainers": pkg_maintainers,
            "acl": pkg_acl,
            "versions": pkg_versions,
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
