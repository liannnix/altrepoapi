from collections import namedtuple

from utils import (
    datetime_to_iso,
    tuplelist_to_dict,
    sort_branches,
    get_nickname_from_packager,
    dp_flags_decode,
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
                link_ += f"?a=tree;hb={subtask['srpm_evr']}"
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
                link_ += f"?a=tree;hb={subtask['srpm_evr']}"
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
        gear_link = ""

        SubtaskMeta = namedtuple(
            "SubtaskMeta",
            ["repo", "id", "sub_id", "type", "dir", "tag_id", "srpm_name", "srpm_evr"],
        )

        self.conn.request_line = self.sql.get_task_gears_by_hash.format(
            pkghash=self.pkghash, branch=self.branch
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
                pkghash=self.pkghash,
                branch=self.branch
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

            pkg_hash = str(response[0][0])
            pkg_version = str(response[0][1])
            pkg_release = str(response[0][2])

            delete_task_info["task_changed"] = datetime_to_iso(delete_task_info["task_changed"])

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


class PackageDownloadLinks(APIWorker):
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

        if self.validation_results != []:
            return False
        else:
            return True

    def get(self):
        self.branch = self.args["branch"]
        bin_pkgs = {}
        #  get package task info
        TaskInfo = namedtuple(
            "TaskInfo",
            [
                "task_id",
                "subtask_id",
                "subtask_arch",
                "titer_srcrpm_hash",
                "titer_pkgs_hash",
            ],
        )
        PkgInfo = namedtuple("PkgInfo", ["file", "arch", "size"])
        self.conn.request_line = self.sql.get_build_task_by_hash.format(
            pkghash=self.pkghash, branch=self.branch
        )
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        if response:
            #  use hashes from task
            use_task = True
            subtasks = [TaskInfo(*el)._asdict() for el in response]
            # get package hashes and archs from Tasks
            for t in subtasks:
                bin_pkgs[t["subtask_arch"]] = {
                    h for h in t["titer_pkgs_hash"] if h != 0
                }
                bin_pkgs[t["subtask_arch"]] = list(bin_pkgs[t["subtask_arch"]])
            # get package file names
            hshs = [self.pkghash] + [h for hs in bin_pkgs.values() for h in hs]
            self.conn.request_line = self.sql.get_pkgs_filename_by_hshs.format(
                hshs=hshs
            )
            status, response = self.conn.send_request()
            if not status:
                self._store_sql_error(response, self.ll.ERROR, 500)
                return self.error
            if not response:
                self._store_error(
                    {
                        "message": f"No package fienames info found in DB",
                        "args": self.args,
                    },
                    self.ll.INFO,
                    404,
                )
                return self.error
            # store filenames and archs as dict
            filenames = {el[0]: PkgInfo(*el[1:]) for el in response}
        else:
            # no task found -> use ftp.altlinux.org
            use_task = False
            # get package hashes and archs from last_packages
            self.conn.request_line = self.sql.get_src_and_binary_pkgs.format(
                pkghash=self.pkghash, branch=self.branch
            )
            status, response = self.conn.send_request()
            if not status:
                self._store_sql_error(response, self.ll.ERROR, 500)
                return self.error
            if not response:
                self._store_error(
                    {
                        "message": f"No package fienames info found in DB",
                        "args": self.args,
                    },
                    self.ll.INFO,
                    404,
                )
                return self.error
            # store filenames and archs as dict
            filenames = {el[0]: PkgInfo(*el[1:]) for el in response}
            for h, f in filenames.items():
                if h != self.pkghash:
                    if f.arch not in bin_pkgs:
                        bin_pkgs[f.arch] = []
                    if h not in bin_pkgs[f.arch]:
                        bin_pkgs[f.arch].append(h)

        # get package files MD5 checksum
        hshs = tuple(filenames.keys())
        self.conn.request_line = self.sql.get_pkgs_md5_by_hshs.format(hshs=hshs)
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        if not response:
            self._store_error(
                {
                    "message": f"No package MD5 info found in DB",
                    "args": self.args,
                },
                self.ll.INFO,
                404,
            )
            return self.error
        md5_sums = {el[0]: el[1] for el in response}

        # pop source package filename
        src_filename = filenames[self.pkghash].file
        src_filesize = filenames[self.pkghash].size
        src_arch = filenames[self.pkghash].arch
        filenames.pop(self.pkghash, None)
        # get source package arch by binary packages
        archs = ["x86_64", "i586"]
        archs += [arch for arch in bin_pkgs.keys() if arch not in archs]
        for arch in archs:
            if arch in bin_pkgs and len(bin_pkgs[arch]) > 0:
                src_arch = arch
                break
        # pop noarch binary packages for archs != src_arch
        for k, v in bin_pkgs.items():
            for p in v:
                if k != src_arch and filenames[p].arch == "noarch":
                    filenames.pop(p, None)

        # get package versions
        pkg_versions = []
        self.conn.request_line = self.sql.get_pkg_versions_by_hash.format(
            pkghash=self.pkghash
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
        # workaround for multiple versions of returned for certain branch
        pkg_versions = [
            PkgVersions(*(b, *pkg_versions[b][-3:]))._asdict() for b in pkg_branches
        ]

        def make_link_to_task(base, task, subtask, arch, filename, is_src):
            return "/".join(
                (
                    base,
                    str(task),
                    "build",
                    str(subtask),
                    arch,
                    "srpm" if is_src else "rpms",
                    filename,
                )
            )

        def make_link_to_repo(base, branch, files, arch, filename, is_src):
            return "/".join(
                (
                    base,
                    branch,
                    files,
                    "" if is_src else arch,
                    "SRPMS" if is_src else "RPMS",
                    filename,
                )
            )

        def bytes2human(size: int) -> str:
            """Convert file size in bytes to human readable string representation."""
            for unit in ["", "K", "M", "G", "T", "P", "E"]:
                if abs(size) < 1024.0:
                    return f"{size:3.1f} {unit}B"
                size /= 1024.0
            return f"{size:.1f} ZB"

        res = {}

        if use_task:
            # build links to task
            task_ = subtasks[0]["task_id"]
            subtask_ = subtasks[0]["subtask_id"]
            task_base_ = "http://git.altlinux.org/tasks"

            res["src"] = [
                {
                    "name": src_filename,
                    "url": make_link_to_task(
                        task_base_,
                        task_,
                        subtask_,
                        src_arch,
                        src_filename,
                        is_src=True,
                    ),
                    "md5": md5_sums[self.pkghash],
                    "size": bytes2human(src_filesize),
                }
            ]

            for k, v in bin_pkgs.items():
                if len(v) > 0:
                    res[k] = []
                    for p in v:
                        if p in filenames:
                            if filenames[p].arch == "noarch":
                                # save noarch packages separatelly
                                if "noarch" not in res:
                                    res["noarch"] = []
                                res["noarch"].append(
                                    {
                                        "name": filenames[p].file,
                                        "url": make_link_to_task(
                                            task_base_,
                                            task_,
                                            subtask_,
                                            k,
                                            filenames[p].file,
                                            is_src=False,
                                        ),
                                        "md5": md5_sums[p],
                                        "size": bytes2human(filenames[p].size),
                                    }
                                )
                            else:
                                res[k].append(
                                    {
                                        "name": filenames[p].file,
                                        "url": make_link_to_task(
                                            task_base_,
                                            task_,
                                            subtask_,
                                            k,
                                            filenames[p].file,
                                            is_src=False,
                                        ),
                                        "md5": md5_sums[p],
                                        "size": bytes2human(filenames[p].size),
                                    }
                                )
        else:
            #  build links to repo
            repo_base_ = "http://ftp.altlinux.org/pub/distributions/ALTLinux"
            if self.branch in lut.taskless_branches:
                branch_, arch_ = self.branch.split("_")
                files_ = "files"
                repo_base_ += f"/ports/{arch_}"
                if branch_ == "sisyphus":
                    branch_ = "Sisyphus"

            elif self.branch == "sisyphus":
                branch_ = "Sisyphus"
                files_ = "files"
            else:
                branch_ = self.branch
                files_ = "branch/files"

            res["src"] = [
                {
                    "name": src_filename,
                    "url": make_link_to_repo(
                        repo_base_,
                        branch_,
                        files_,
                        src_arch,
                        src_filename,
                        is_src=True,
                    ),
                    "md5": md5_sums[self.pkghash],
                    "size": bytes2human(src_filesize),
                }
            ]

            for k, v in bin_pkgs.items():
                if len(v) > 0:
                    res[k] = []
                    for p in v:
                        if p in filenames:
                            res[k].append(
                                {
                                    "name": filenames[p].file,
                                    "url": make_link_to_repo(
                                        repo_base_,
                                        branch_,
                                        files_,
                                        k,
                                        filenames[p].file,
                                        is_src=False,
                                    ),
                                    "md5": md5_sums[p],
                                    "size": bytes2human(filenames[p].size),
                                }
                            )

        res = {
            "pkghash": str(self.pkghash),
            "request_args": self.args,
            "downloads": [
                {"arch": k, "packages": v} for k, v in res.items() if len(v) > 0
            ],
            "versions": pkg_versions,
        }

        return res, 200


class PackagesBinaryListInfo(APIWorker):
    """Retrieves all binary package architecture."""

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
