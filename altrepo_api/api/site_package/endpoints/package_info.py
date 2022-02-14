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
                f"changelog history length should be not less than 1"
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
        # get package info
        pkg_src_or_bin = f"AND pkg_sourcepackage = {source}"
        self.conn.request_line = self.sql.get_pkg_info.format(
            pkghash=self.pkghash, source=pkg_src_or_bin
        )
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        if not response:
            self._store_error(
                {
                    "message": f"No packages found in last packages with hash {self.pkghash}",
                    "args": self.args,
                },
                self.ll.INFO,
                404,
            )
            return self.error
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

        self.conn.request_line = self.sql.get_task_gears_by_hash.format(
            pkghash=self.pkghash
        )
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
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
        # clear pkg_tasks fro taskless branches
        if self.branch in lut.taskless_branches:
            pkg_task = 0
            pkg_tasks = []
            pkg_task_date = None
        # get package maintainers from changelog
        pkg_maintainers = []
        self.conn.request_line = self.sql.get_pkg_maintainers.format(
            pkghash=self.pkghash
        )
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        for el in response[0][0]:
            if "altlinux" in el:
                nickname = get_nickname_from_packager(el)
                if nickname not in pkg_maintainers:
                    pkg_maintainers.append(nickname)
        # get package ACLs
        pkg_acl = []
        self.conn.request_line = self.sql.get_pkg_acl.format(
            name=pkg_info["name"], branch=self.branch
        )
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        if response:
            pkg_acl = response[0][0]
        # get package versions
        pkg_versions = []
        if source:
            self.conn.request_line = self.sql.get_pkg_versions.format(
                name=pkg_info["name"]
            )
        else:
            self.conn.request_line = self.sql.get_pkg_binary_versions.format(
                name=pkg_info["name"], arch=pkg_info["arch"]
            )
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        PkgVersions = namedtuple(
            "PkgVersions", ["branch", "version", "release", "pkghash"]
        )
        # sort package versions by branch
        pkg_branches = sort_branches([el[0] for el in response])
        pkg_versions = tuplelist_to_dict(response, 3)
        # FIXME: workaround for multiple versions of returned for certain branch
        pkg_versions = [
            PkgVersions(*(b, *pkg_versions[b][-3:]))._asdict() for b in pkg_branches
        ]

        # get package dependencies
        pkg_dependencies = []
        if source == 1:
            self.conn.request_line = self.sql.get_pkg_dependencies.format(
                pkghash=self.pkghash
            )
            status, response = self.conn.send_request()
            if not status:
                self._store_sql_error(response, self.ll.ERROR, 500)
                return self.error
            PkgDependencies = namedtuple("PkgDependencies", ["name", "version", "flag"])
            pkg_dependencies = [PkgDependencies(*el)._asdict() for el in response]

            # change numeric flag on text
            for el in pkg_dependencies:
                el["flag_decoded"] = dp_flags_decode(el["flag"], lut.rpmsense_flags)

        # get provided binary and source packages
        package_archs = {}
        if source:
            self.conn.request_line = self.sql.get_binary_pkgs.format(
                pkghash=self.pkghash, branch=self.branch
            )
        else:
            self.conn.request_line = self.sql.get_source_pkgs.format(
                pkghash=self.pkghash
            )
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error

        if response:
            if source:
                pkg_info["buildtime"] = response[0][2]
                for elem in response:
                    package_archs[elem[0]] = {el[0]: str(el[1]) for el in elem[1]}
            else:
                for elem in response:
                    package_archs[elem[0]] = {"src": str(elem[1])}
        # get package changelog
        self.conn.request_line = (
            self.sql.get_pkg_changelog,
            {"pkghash": self.pkghash, "limit": self.chlog_length},
        )
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        if not response:
            self._store_error(
                {
                    "message": f"No packages found in last packages with hash {self.pkghash}",
                    "args": self.args,
                },
                self.ll.INFO,
                404,
            )
            return self.error

        Changelog = namedtuple("Changelog", ["date", "name", "evr", "message"])
        changelog_list = [
            Changelog(datetime_to_iso(el[1]), *el[2:])._asdict() for el in response
        ]

        # get package beehive rebuild status
        if self.branch not in lut.known_beehive_branches:
            # return empty result list if branch not in beehive branches
            bh_status = []
        else:
            # get last beehive errors by package hash
            self.conn.request_line = (
                self.sql.get_last_bh_rebuild_status_by_hsh,
                {"pkghash": self.pkghash, "branch": self.branch},
            )
            status, response = self.conn.send_request()
            if not status:
                self._store_sql_error(response, self.ll.ERROR, 500)
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
            self.conn.request_line = self.sql.get_deleted_package_task_by_src.format(
                name=self.name, branch=self.branch
            )
        else:
            # get task info where source package of input binary was deleted
            self.conn.request_line = self.sql.get_deleted_package_task_by_bin.format(
                name=self.name, branch=self.branch
            )
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        TaskMeta = namedtuple(
            "TaskMeta",
            ["task_id", "subtask_id", "task_changed", "task_owner", "subtask_userid"],
        )
        if response:
            delete_task_info = TaskMeta(*response[0])._asdict()

            # task in wich source package was deleted found
            # get task message
            delete_task_info["task_message"] = ""
            self.conn.request_line = self.sql.get_delete_task_message.format(
                task_id=delete_task_info["task_id"],
                task_changed=delete_task_info["task_changed"],
            )
            status, response = self.conn.send_request()
            if not status:
                self._store_sql_error(response, self.ll.ERROR, 500)
                return self.error
            if response:
                delete_task_info["task_message"] = response[0][0]
            # get last package version info from branch
            if source:
                self.conn.request_line = (
                    self.sql.get_srcpkg_hash_for_branch_on_date.format(
                        name=self.name,
                        branch=self.branch,
                        task_changed=delete_task_info["task_changed"],
                    )
                )
            else:
                self.conn.request_line = (
                    self.sql.get_binpkg_hash_for_branch_on_date.format(
                        arch=self.arch,
                        name=self.name,
                        branch=self.branch,
                        task_changed=delete_task_info["task_changed"],
                    )
                )
            status, response = self.conn.send_request()
            if not status:
                self._store_sql_error(response, self.ll.ERROR, 500)
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
                self.conn.request_line = self.sql.get_last_build_task_by_pkg.format(
                    preselect=presel_sql,
                    branch=self.branch,
                    task_changed=delete_task_info["task_changed"],
                )
                status, response = self.conn.send_request()
                if not status:
                    self._store_sql_error(response, self.ll.ERROR, 500)
                    return self.error
                # nothing helped to find out package history
                if not response:
                    self._store_error(
                        {
                            "message": f"No information about deleting package {self.name} from {self.branch} was found",
                            "args": self.args,
                        },
                        self.ll.INFO,
                        404,
                    )
                    return self.error

                pkg_hash = str(response[0][1])
                pkg_version = str(response[0][2])
                pkg_release = str(response[0][3])

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
        else:
            # task in wich source package was deleted not found
            arch_ = ""
            if not source:
                arch_ = f"with {self.arch} arch "
            self._store_error(
                {
                    "message": f"No information about deleting package {self.name} {arch_}from {self.branch} was found",
                    "args": self.args,
                },
                self.ll.INFO,
                404,
            )
            return self.error


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

        self.conn.request_line = self.sql.get_pkgs_binary_list.format(
            branch=self.branch, name=self.name
        )
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        if not response:
            self._store_error(
                {
                    "message": f"No found",
                    "args": self.args,
                },
                self.ll.INFO,
                404,
            )
            return self.error

        PkgMeta = namedtuple(
            "PkgMeta",
            ["hash", "name", "version", "release", "arch"],
        )

        retval = [PkgMeta(*el)._asdict() for el in response]

        # get package versions
        pkg_versions = []
        self.conn.request_line = self.sql.get_pkg_binary_list_versions.format(
            name=retval[0]["name"]
        )
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        PkgVersions = namedtuple("PkgVersions", ["branch", "version", "release"])
        # sort package versions by branch
        pkg_branches = sort_branches([el[0] for el in response])
        pkg_versions = tuplelist_to_dict(response, 3)
        # FIXME: workaround for multiple versions of returned for certain branch
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
