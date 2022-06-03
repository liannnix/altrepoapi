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
    tuplelist_to_dict,
    sort_branches,
    bytes2human,
)

from altrepo_api.api.base import APIWorker
from altrepo_api.api.misc import lut
from ..sql import sql


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


def make_link_to_task_arepo(base, task, filename):
    return "/".join(
        (
            base,
            str(task),
            "build/repo/x86_64-i586/RPMS.task",
            filename,
        )
    )


class PackageDownloadLinks(APIWorker):
    """Build source and binary packages downloads links."""

    def __init__(self, connection, pkghash, **kwargs):
        self.pkghash = pkghash
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        return True

    def get(self):
        self.branch = self.args["branch"]
        bin_pkgs = {}
        # return no download links from sisyphus_e2k branch
        if self.branch in lut.no_downloads_branches:
            return {
                "pkghash": str(self.pkghash),
                "request_args": self.args,
                "downloads": [],
                "versions": [],
            }, 200
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
        subtasks = []
        if response:
            #  use hashes from task
            use_task = True
            subtasks = [TaskInfo(*el)._asdict() for el in response]
            # get package hashes and archs from Tasks
            for t in subtasks:
                bin_pkgs[t["subtask_arch"]] = list(
                    {h for h in t["titer_pkgs_hash"] if h != 0}
                )
            # get package file names
            hshs = [self.pkghash] + [h for hs in bin_pkgs.values() for h in hs]
            self.conn.request_line = self.sql.get_pkgs_filename_by_hshs.format(
                hshs=tuple(set(hshs))
            )
            status, response = self.conn.send_request()
            if not status:
                self._store_sql_error(response, self.ll.ERROR, 500)
                return self.error
            if not response:
                self._store_error(
                    {
                        "message": "No package fienames info found in DB",
                        "args": self.args,
                    },
                    self.ll.INFO,
                    404,
                )
                return self.error
            # store filenames and archs as dict
            filenames = {el[0]: PkgInfo(*el[1:]) for el in response}
            # try to find 'arepo' packages from task
            if "i586" in bin_pkgs:
                # get all 'x86_64-i586' packages from task plan
                self.conn.request_line = self.sql.get_arepo_pkgs_by_task.format(
                    taskid=subtasks[0]["task_id"]
                )
                status, response = self.conn.send_request()
                if not status:
                    self._store_sql_error(response, self.ll.ERROR, 500)
                    return self.error
                if response:
                    # store filenames and archs as dict
                    arepo_filenames = {el[0]: PkgInfo(*el[1:]) for el in response}
                    # filter packages using package file name from 'i586' arch
                    i586_pkg_files = {
                        p.file for p in filenames.values() if p.arch == "i586"
                    }
                    for hash, pkg in list(arepo_filenames.items()):
                        fname = pkg.file.replace("i586-", "")
                        if fname not in i586_pkg_files:
                            del arepo_filenames[hash]
                    filenames.update(arepo_filenames)
                    # update bin_pkgs with arepo packages
                    bin_pkgs["x86_64-i586"] = list({h for h in arepo_filenames})
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
                        "message": "No package filenames info found in DB",
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
                    "message": "No package MD5 info found in DB",
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
        # keep only 'noarch' packages from src_arch iteration
        filenames_noarch = {k: v for k, v in filenames.items() if v.arch == "noarch"}
        filenames = {k: v for k, v in filenames.items() if v.arch != "noarch"}
        # append 'noarch' packages only from src_arch iteration
        for p in bin_pkgs[src_arch]:
            if p in filenames_noarch:
                filenames[p] = filenames_noarch[p]
        # remove 'noarch' packages form not src_arch iterations
        for h in filenames_noarch:
            for arch in [x for x in archs if x in bin_pkgs and x != src_arch]:
                bin_pkgs[arch] = [x for x in bin_pkgs[arch] if x != h]
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
        pkg_branches = sort_branches([el[0] for el in response])  # type: ignore
        pkg_versions = tuplelist_to_dict(response, 3)  # type: ignore
        # workaround for multiple versions of returned for certain branch
        pkg_versions = [
            PkgVersions(*(b, *pkg_versions[b][-3:]))._asdict() for b in pkg_branches
        ]

        res = {}

        if use_task:
            # build links to task
            task_ = subtasks[0]["task_id"]
            subtask_ = subtasks[0]["subtask_id"]
            task_base_ = lut.gitalt_tasks_base

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
                            elif filenames[p].arch == "x86_64-i586":
                                res[k].append(
                                    {
                                        "name": filenames[p].file,
                                        "url": make_link_to_task_arepo(
                                            task_base_,
                                            task_,
                                            filenames[p].file,
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
            repo_base_ = lut.public_ftp_base
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


class BinaryPackageDownloadLinks(APIWorker):
    """Build binary package downloads link."""

    def __init__(self, connection, pkghash, **kwargs):
        self.pkghash = pkghash
        self.conn = connection
        self.args = kwargs
        self.sql = sql
        super().__init__()

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        return True

    def get(self):
        self.branch = self.args["branch"]
        self.arch = self.args["arch"]

        # return no download links from sisyphus_e2k branch
        if self.branch in lut.no_downloads_branches:
            return {
                "pkghash": str(self.pkghash),
                "request_args": self.args,
                "downloads": [],
                "versions": [],
            }, 200

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
        self.conn.request_line = self.sql.get_build_task_by_bin_hash.format(
            pkghash=self.pkghash, branch=self.branch
        )
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        subtask = {}
        if response:
            #  use hashes from task
            use_task = True
            subtask = TaskInfo(*response[0])._asdict()  # type: ignore
            # get package file name
            self.conn.request_line = self.sql.get_pkgs_filename_by_hshs.format(
                hshs=(self.pkghash,)
            )
            status, response = self.conn.send_request()
            if not status:
                self._store_sql_error(response, self.ll.ERROR, 500)
                return self.error
            if not response:
                self._store_error(
                    {
                        "message": "No package fienames info found in DB",
                        "args": self.args,
                    },
                    self.ll.INFO,
                    404,
                )
                return self.error
            # store package file info
            filename = PkgInfo(*response[0][1:])  # type: ignore
        else:
            # no task found -> use ftp.altlinux.org
            use_task = False
            # get package hashes and archs from last_packages
            self.conn.request_line = self.sql.get_bin_pkg_from_last.format(
                pkghash=self.pkghash, branch=self.branch, arch=self.arch
            )
            status, response = self.conn.send_request()
            if not status:
                self._store_sql_error(response, self.ll.ERROR, 500)
                return self.error
            if not response:
                self._store_error(
                    {
                        "message": "No package info found in DB",
                        "args": self.args,
                    },
                    self.ll.INFO,
                    404,
                )
                return self.error
            # store package file info
            filename = PkgInfo(*response[0][1:])  # type: ignore

        # get package files MD5 checksum
        self.conn.request_line = self.sql.get_pkgs_md5_by_hshs.format(
            hshs=(self.pkghash,)
        )
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        if not response:
            self._store_error(
                {
                    "message": "No package MD5 info found in DB",
                    "args": self.args,
                },
                self.ll.INFO,
                404,
            )
            return self.error
        md5_sum = response[0][1]  # type: ignore

        # get package versions
        pkg_versions = []
        self.conn.request_line = self.sql.get_bin_pkg_versions_by_hash.format(
            pkghash=self.pkghash, arch=self.arch
        )
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        PkgVersions = namedtuple(
            "PkgVersions", ["branch", "version", "release", "pkghash", "arch"]
        )
        # sort package versions by branch
        pkg_branches = sort_branches([el[0] for el in response])  # type: ignore
        pkg_versions = tuplelist_to_dict(response, 4)  # type: ignore
        # workaround for multiple versions of returned for certain branch
        pkg_versions = [
            PkgVersions(*(b, *pkg_versions[b][-4:]))._asdict() for b in pkg_branches
        ]

        res = {}

        if use_task:
            # build links to task
            task_base_ = lut.gitalt_tasks_base

            if filename.arch == "noarch":
                # save noarch packages separatelly
                res["noarch"] = []
                res["noarch"].append(
                    {
                        "name": filename.file,
                        "url": make_link_to_task(
                            task_base_,
                            subtask["task_id"],
                            subtask["subtask_id"],
                            subtask["subtask_arch"],
                            filename.file,
                            is_src=False,
                        ),
                        "md5": md5_sum,
                        "size": bytes2human(filename.size),
                    }
                )
            else:
                res[subtask["subtask_arch"]] = []
                res[subtask["subtask_arch"]].append(
                    {
                        "name": filename.file,
                        "url": make_link_to_task(
                            task_base_,
                            subtask["task_id"],
                            subtask["subtask_id"],
                            subtask["subtask_arch"],
                            filename.file,
                            is_src=False,
                        ),
                        "md5": md5_sum,
                        "size": bytes2human(filename.size),
                    }
                )
        else:
            #  build links to repo
            repo_base_ = lut.public_ftp_base
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

            res[self.arch] = []
            res[self.arch].append(
                {
                    "name": filename.file,
                    "url": make_link_to_repo(
                        repo_base_,
                        branch_,
                        files_,
                        self.arch,
                        filename.file,
                        is_src=False,
                    ),
                    "md5": md5_sum,
                    "size": bytes2human(filename.size),
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
