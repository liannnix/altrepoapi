from collections import namedtuple

from utils import (
    datetime_to_iso,
    tuplelist_to_dict,
    sort_branches,
    get_nickname_from_packager,
)

from api.base import APIWorker
from api.misc import lut
from database.site_sql import sitesql


class PackageChangelog(APIWorker):
    """Retrieves package changelog from DB."""

    def __init__(self, connection, pkghash, **kwargs):
        self.pkghash = pkghash
        self.conn = connection
        self.args = kwargs
        self.sql = sitesql
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

    def get(self):
        self.chlog_length = self.args["changelog_last"]
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
        changelog_list = [Changelog(*el[1:])._asdict() for el in response]

        res = {
            "pkghash": str(self.pkghash),
            "request_args": self.args,
            "length": len(changelog_list),
            "changelog": changelog_list,
        }

        return res, 200


class PackageInfo(APIWorker):
    """Retrieves package info from DB."""

    def __init__(self, connection, pkghash, **kwargs):
        self.pkghash = pkghash
        self.conn = connection
        self.args = kwargs
        self.sql = sitesql
        super().__init__()

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        self.validation_results = []

        if self.args["branch"] == "" or self.args["branch"] not in lut.known_branches:
            self.validation_results.append(
                f"unknown package set name : {self.args['branch']}"
            )
            self.validation_results.append(
                f"allowed package set names are : {lut.known_branches}"
            )

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
        link_ = ""
        if subtask["type"] == "copy":
            # 'copy' always has only 'subtask_package'
            link_ = pkgname
        elif subtask["type"] == "delete" and subtask["srpm_name"] != "":
            # TODO: bug workaround for girar changes @ e74d8067009d
            link_ = f"{git_base_url}/srpms/{pkgname[0]}/{pkgname}.git"
            if subtask["srpm_evr"] != "":
                link_ += f"?a=commit;hb={subtask['srpm_evr']}"
        elif subtask["type"] == "delete":
            # 'delete' return only package name
            link_ = pkgname
        elif subtask["dir"] != "" or subtask["type"] == "gear":
            # 'gear' and 'rebuild' + 'unknown' with gears
            link_ = f"{git_base_url}/gears/{pkgname[0]}/{pkgname}.git"
            if subtask["tag_id"] != "":
                link_ += f"?a=commit;hb={subtask['tag_id']}"
        elif subtask["srpm_name"] != "" or subtask["type"] == "srpm":
            # 'srpm' and 'rebuild' + 'unknown' with srpm
            link_ = f"{git_base_url}/srpms/{pkgname[0]}/{pkgname}.git"
            if subtask["srpm_evr"] != "":
                link_ += f"?a=commit;hb={subtask['srpm_evr']}"
        return link_

    def get(self):
        self.branch = self.args["branch"]
        self.chlog_length = self.args["changelog_last"]
        PkgMeta = namedtuple(
            "PkgMeta",
            [
                "name",
                "version",
                "release",
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
        self.conn.request_line = self.sql.get_pkg_info.format(pkghash=self.pkghash)
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
        gear_link = ""

        SubtaskMeta = namedtuple(
            "SubtaskMeta",
            ["repo", "id", "sub_id", "type", "dir", "tag_id", "srpm_name", "srpm_evr"],
        )

        self.conn.request_line = self.sql.get_task_gears_by_hash.format(
            pkghash=self.pkghash
        )
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        if response:
            tasks_list = [SubtaskMeta(*el)._asdict() for el in response]
            for task in tasks_list:
                if task["repo"] == self.branch:
                    pkg_task = task["id"]
                    if task["type"] != "copy":
                        pkg_tasks.append({"type": "build", "id": pkg_task})
                        gear_link = self._parse_task_gear(
                            pkg_info["name"], task, lut.gitalt_base
                        )
                        break
                    else:
                        pkg_tasks.append({"type": "copy", "id": pkg_task})
                else:
                    if task["type"] != "copy":
                        pkg_task = task["id"]
                        gear_link = self._parse_task_gear(
                            pkg_info["name"], task, lut.gitalt_base
                        )
                        pkg_tasks.append({"type": "build", "id": pkg_task})
                        break
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
        self.conn.request_line = self.sql.get_pkg_versions.format(name=pkg_info["name"])
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
        # get provided binary packages
        bin_packages_list = []
        self.conn.request_line = self.sql.get_binary_pkgs.format(pkghash=self.pkghash)
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        bin_packages_list = [el[0] for el in response]
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
            BeehiveStatus = namedtuple("BeehiveStatus", ["arch", "status", "build_time", "updated", "ftbfs_since"])
            bh_status = [BeehiveStatus(*el)._asdict() for el in response]
            for bh in bh_status:
                epoch_ = pkg_info["epoch"]
                if epoch_ == 0:
                    epoch_version = pkg_info["version"]
                else:
                    epoch_version = str(epoch_) + ":" + pkg_info["version"]

                url = "/".join((
                    lut.beehive_base,
                    "logs",
                    "Sisyphus" if self.branch == "sisyphus" else self.branch,
                    bh["arch"],
                    "archive",
                    bh["updated"].strftime("%Y/%m%d"),
                    "error",
                    "-".join((
                        pkg_info["name"],
                        epoch_version,
                        pkg_info["release"]
                    )),
                ))
                if bh["status"] == "error":
                    bh["url"] = url
                else:
                    bh["url"] = ""
                bh["updated"] = datetime_to_iso(bh["updated"])
                bh["ftbfs_since"] = datetime_to_iso(bh["ftbfs_since"])

        res = {
            "pkghash": str(self.pkghash),
            "request_args": self.args,
            **pkg_info,
            "task": pkg_task,
            "gear": gear_link,
            "tasks": pkg_tasks,
            "packages": bin_packages_list,
            "changelog": changelog_list,
            "maintainers": pkg_maintainers,
            "acl": pkg_acl,
            "versions": pkg_versions,
            "beehive": bh_status,
        }

        return res, 200


class DeletedPackageInfo(APIWorker):
    """Retrieves information about deleted package."""

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sitesql
        super().__init__()

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        self.validation_results = []

        if self.args["branch"] == "" or self.args["branch"] not in lut.known_branches:
            self.validation_results.append(
                f"unknown package set name : {self.args['branch']}"
            )
            self.validation_results.append(
                f"allowed package set names are : {lut.known_branches}"
            )

        if self.args["name"] == "":
            self.validation_results.append(f"package name should not be empty string")

        if self.validation_results != []:
            return False
        else:
            return True

    def get(self):
        self.branch = self.args["branch"]
        self.name = self.args["name"]

        self.conn.request_line = self.sql.get_deleted_package_task.format(
            name=self.name, branch=self.branch
        )
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        if not response:
            self._store_error(
                {
                    "message": f"No information about deleting package {self.name} from {self.branch} found",
                    "args": self.args,
                },
                self.ll.INFO,
                404,
            )
            return self.error

        TaskMeta = namedtuple(
            "TaskMeta",
            ["task_id", "subtask_id", "task_changed", "task_owner", "subtask_userid"],
        )
        delete_task_info = TaskMeta(*response[0])._asdict()

        self.conn.request_line = self.sql.get_srcpkg_hash_for_branch_on_date.format(
            name=self.name,
            branch=self.branch,
            task_changed=delete_task_info["task_changed"],
        )
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        if not response:
            self._store_error(
                {
                    "message": f"No information about deleting package {self.name} from {self.branch} found",
                    "args": self.args,
                },
                self.ll.INFO,
                404,
            )
            return self.error

        pkg_hash = str(response[0][0])
        pkg_version = str(response[0][1])
        pkg_release = str(response[0][2])

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


class LastPackagesWithCVEFix(APIWorker):
    """Retrieves information about last packages with CVE's in changelog."""

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sitesql
        super().__init__()

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        self.validation_results = []

        if self.args["branch"] == "" or self.args["branch"] not in lut.known_branches:
            self.validation_results.append(
                f"unknown package set name : {self.args['branch']}"
            )
            self.validation_results.append(
                f"allowed package set names are : {lut.known_branches}"
            )

        if self.validation_results != []:
            return False
        else:
            return True

    def get(self):
        self.branch = self.args["branch"]

        self.conn.request_line = self.sql.get_last_packages_with_cve_fixes.format(
            branch=self.branch
        )
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        if not response:
            self._store_error(
                {
                    "message": f"No packages with recent CVE fixes from {self.branch} found",
                    "args": self.args,
                },
                self.ll.INFO,
                404,
            )
            return self.error

        PackageMeta = namedtuple(
            "PackageMeta",
            [
                "name",
                "version",
                "release",
                "buildtime",
                "summary",
                "changelog_date",
                "changelog_text",
            ],
        )

        packages = [
            dict(hash=str(el[0]), **PackageMeta(*el[1:])._asdict()) for el in response
        ]
        for package in packages:
            package["changelog_date"] = datetime_to_iso(package["changelog_date"])

        res = {"request_args": self.args, "length": len(packages), "packages": packages}

        return res, 200
