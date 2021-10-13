from collections import namedtuple

from utils import tuplelist_to_dict, sort_branches, datetime_to_iso
from utils import get_nickname_from_packager

from api.base import APIWorker
from api.misc import lut
from database.site_sql import sitesql


class PackagesetPackages(APIWorker):
    """Retrieves packages information in given package set."""

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

        if self.args["package_type"] not in ("source", "binary", "all"):
            self.validation_results.append(
                f"package type should be one of 'source', 'binary' or 'all' not '{self.args['package_type']}'"
            )

        if self.args["group"]:
            if self.args["group"] not in lut.pkg_groups:
                self.validation_results.append(
                    f"unknown package category : {self.args['group']}"
                )
                self.validation_results.append(
                    f"allowed package categories : {lut.pkg_groups}"
                )

        if self.args["buildtime"] and self.args["buildtime"] < 0:
            self.validation_results.append(
                f"package build time should be integer UNIX time representation"
            )

        if self.validation_results != []:
            return False
        else:
            return True

    def get(self):
        self.pkg_type = self.args["package_type"]
        self.branch = self.args["branch"]
        self.group = self.args["group"]
        self.buildtime = self.args["buildtime"]

        if self.group is not None:
            group = f"AND pkg_group_ = %(group)s"
        else:
            group = ""
            self.group = ""

        pkg_type_to_sql = {"source": (1,), "binary": (0,), "all": (1, 0)}
        sourcef = pkg_type_to_sql[self.pkg_type]

        self.conn.request_line = (
            self.sql.get_repo_packages.format(src=sourcef, group=group),
            {"buildtime": self.buildtime, "branch": self.branch, "group": self.group},
        )
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        if not response:
            self._store_error(
                {
                    "message": f"No data found in database for given parameters",
                    "args": self.args,
                },
                self.ll.INFO,
                404,
            )
            return self.error

        PkgMeta = namedtuple(
            "PkgMeta",
            [
                "hash",
                "name",
                "version",
                "release",
                "buildtime",
                "summary",
                "maintainer",
                "category",
                "changelog",
            ],
        )

        retval = [PkgMeta(*el)._asdict() for el in response]

        res = {"request_args": self.args, "length": len(retval), "packages": retval}
        return res, 200


class PackagesetPackageHash(APIWorker):
    """Retrieves package hash by package name in package set."""

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

        self.conn.request_line = self.sql.get_pkghash_by_name.format(
            branch=self.branch, name=self.name
        )
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        if not response:
            self._store_error(
                {
                    "message": f"Package '{self.name}' not found in package set '{self.branch}'",
                    "args": self.args,
                },
                self.ll.INFO,
                404,
            )
            return self.error

        res = {
            "request_args": self.args,
            "pkghash": str(response[0][0]),
            "version": response[0][1],
            "release": response[0][2],
        }
        return res, 200


class PackagesetPackageBinaryHash(APIWorker):
    """Retrieves package hash by package binary name in package set."""

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

        if self.args["arch"] == "" or self.args["arch"] not in lut.known_archs:
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
        self.arch = self.args["arch"]
        self.name = self.args["name"]

        self.conn.request_line = self.sql.get_pkghash_by_binary_name.format(
            branch=self.branch, arch=self.arch, name=self.name
        )
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        if not response:
            self._store_error(
                {
                    "message": f"Package '{self.name}' architecture {self.arch} not found in package set '{self.branch}'",
                    "args": self.args,
                },
                self.ll.INFO,
                404,
            )
            return self.error

        res = {
            "request_args": self.args,
            "pkghash": str(response[0][0]),
            "version": response[0][1],
            "release": response[0][2],
        }
        return res, 200


class PackagesetFindPackages(APIWorker):
    """Finds packages in given package set by name relevance."""

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sitesql
        super().__init__()

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        self.validation_results = []

        if self.args["branch"] is not None:
            if (
                self.args["branch"] == ""
                or self.args["branch"] not in lut.known_branches
            ):
                self.validation_results.append(
                    f"unknown package set name : {self.args['branch']}"
                )
                self.validation_results.append(
                    f"allowed package set names are : {lut.known_branches}"
                )

        if self.args["arch"] is not None:
            if self.args["arch"] not in lut.known_archs:
                self.validation_results.append(
                    f"unknown package arch : {self.args['arch']}"
                )
                self.validation_results.append(f"allowed archs are : {lut.known_archs}")

        if self.args["name"] is None or self.args["name"] == "":
            self.validation_results.append(f"package name should not be empty string")
        elif len(self.args["name"]) < 2:
            self.validation_results.append(
                f"package name should be 2 characters at least"
            )

        if self.validation_results != []:
            return False
        else:
            return True

    @staticmethod
    def _relevance_sort(pkgs_dict, pkg_name):
        """Dumb sorting for package names by relevance."""

        def relevance_weight(instr, substr):
            return len(instr) + 100 * instr.find(substr)

        l_in = []
        l_out = []
        for k in pkgs_dict.keys():
            if k.lower().find(pkg_name.lower()) == -1:
                l_out.append(k)
            else:
                l_in.append(k)
        l_in.sort(key=lambda x: relevance_weight(x.lower(), pkg_name.lower()))
        l_out.sort()
        return [(name, *pkgs_dict[name]) for name in (l_in + l_out)]

    def get(self):
        self.name = self.args["name"]
        self.arch = ""
        self.branch = ""
        if self.args["branch"] is not None:
            self.branch = f"AND pkgset_name = '{self.args['branch']}'"
        if self.args["arch"] is not None:
            self.arch = f"AND pkg_arch IN {(self.args['arch'],)}"
        else:
            self.arch = f"AND pkg_arch IN {(*lut.default_archs,)}"

        self.conn.request_line = self.sql.get_find_packages_by_name.format(
            branch=self.branch, name=self.name, arch=self.arch
        )
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        if not response:
            self._store_error(
                {
                    "message": f"Packages like '{self.name}' not found in database",
                    "args": self.args,
                },
                self.ll.INFO,
                404,
            )
            return self.error

        pkgs_sorted = self._relevance_sort(tuplelist_to_dict(response, 5), self.name)

        res = []
        PkgMeta = namedtuple("PkgMeta", ["branch", "version", "release", "pkghash"])
        for pkg in pkgs_sorted:
            res.append(
                {
                    "name": pkg[0],
                    "buildtime": pkg[2],
                    "url": pkg[3],
                    "summary": pkg[4],
                    "category": pkg[5],
                    "versions": [PkgMeta(*el)._asdict() for el in pkg[1]],
                }
            )

        res = {"request_args": self.args, "length": len(res), "packages": res}
        return res, 200


class AllPackagesets(APIWorker):
    """Retrieves package sets names and source packages count."""

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sitesql
        super().__init__()

    def get(self):
        self.conn.request_line = self.sql.get_all_pkgset_names
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        if not response:
            self._store_error(
                {"message": f"No data not found in database", "args": self.args},
                self.ll.INFO,
                404,
            )
            return self.error

        pkg_branches = sort_branches(response[0][0])
        res = [{"branch": b, "count": 0} for b in pkg_branches]

        res = {"length": len(res), "branches": res}
        return res, 200

    def get_with_pkgs_count(self):
        self.conn.request_line = self.sql.get_all_pkgset_names_with_pkg_count
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        if not response:
            self._store_error(
                {"message": f"No data not found in database", "args": self.args},
                self.ll.INFO,
                404,
            )
            return self.error

        PkgCount = namedtuple("PkgCount", ["branch", "count"])
        # sort package counts by branch
        pkg_branches = sort_branches([el[0] for el in response])
        pkg_counts = {el[0]: el[1] for el in response}
        res = [PkgCount(*(b, pkg_counts[b]))._asdict() for b in pkg_branches]

        res = {"length": len(res), "branches": res}
        return res, 200

    def get_summary(self):
        self.conn.request_line = self.sql.get_all_pkgsets_with_src_cnt_by_bin_archs
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        if not response:
            self._store_error(
                {"message": f"No data not found in database", "args": self.args},
                self.ll.INFO,
                404,
            )
            return self.error

        PkgCount = namedtuple("PkgCount", ["branch", "arch", "count"])
        counts = {}

        for cnt in [PkgCount(*el) for el in response]:
            if cnt.branch not in counts:
                counts[cnt.branch] = []
            counts[cnt.branch].append({"arch": cnt.arch, "count": cnt.count})

        # sort package counts by branch
        res = [{"branch": br, "packages_count": counts[br]} for br in sort_branches(counts.keys())]

        res = {"length": len(res), "branches": res}
        return res, 200


class PkgsetCategoriesCount(APIWorker):
    """Retrieves package sets categories and packages count."""

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sitesql
        super().__init__()

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        self.validation_results = []

        if self.args["branch"] is not None:
            if (
                self.args["branch"] == ""
                or self.args["branch"] not in lut.known_branches
            ):
                self.validation_results.append(
                    f"unknown package set name : {self.args['branch']}"
                )
                self.validation_results.append(
                    f"allowed package set names are : {lut.known_branches}"
                )

        if self.args["package_type"] not in ("source", "binary", "all"):
            self.validation_results.append(
                f"package type should be one of 'source', 'binary' or 'all' not '{self.args['package_type']}'"
            )

        if self.validation_results != []:
            return False
        else:
            return True

    def get(self):
        self.branch = self.args["branch"]
        self.pkg_type = self.args["package_type"]

        pkg_type_to_sql = {"source": (1,), "binary": (0,), "all": (1, 0)}
        sourcef = pkg_type_to_sql[self.pkg_type]

        self.conn.request_line = self.sql.get_pkgset_groups_count.format(
            branch=self.branch, sourcef=sourcef
        )
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        if not response:
            self._store_error(
                {"message": f"No data not found in database", "args": self.args},
                self.ll.INFO,
                404,
            )
            return self.error

        res = [{"category": el[0], "count": el[1]} for el in response]

        res = {"request_args": self.args, "length": len(res), "categories": res}
        return res, 200


class AllPackagesetArchs(APIWorker):
    """Retrieves package sets architectures and source packages count by binary packages architecture."""

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
        self.conn.request_line = self.sql.get_all_bin_pkg_archs.format(
            branch=self.branch
        )
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        if not response:
            self._store_error(
                {"message": f"No data not found in database", "args": self.args},
                self.ll.INFO,
                404,
            )
            return self.error

        archs = sorted([x for x in response[0][0] if x not in ("x86_64-i586",)])
        res = [x for x in archs if x.startswith("x")]
        res += [x for x in archs if x.startswith("i")]
        res += [x for x in archs if x.startswith("n")]
        res += sorted([x for x in archs if x not in res])

        res = [{"arch": x, "count": 0} for x in res]

        res = {"length": len(res), "archs": res}
        return res, 200

    def get_with_src_count(self):
        self.branch = self.args["branch"]
        self.conn.request_line = self.sql.get_all_src_cnt_by_bin_archs.format(
            branch=self.branch
        )
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        if not response:
            self._store_error(
                {"message": f"No data not found in database", "args": self.args},
                self.ll.INFO,
                404,
            )
            return self.error

        archs = sorted(
            [(*el,) for el in response], key=lambda val: val[1], reverse=True
        )
        res = [{"arch": x[0], "count": x[1]} for x in archs]

        res = {"length": len(res), "archs": res}
        return res, 200


class AllPackagesetsByHash(APIWorker):
    """Gets all package sets information which include given package hash."""

    def __init__(self, connection, pkghash, **kwargs):
        self.pkghash = pkghash
        self.conn = connection
        self.args = kwargs
        self.sql = sitesql
        super().__init__()

    def get(self):
        self.conn.request_line = self.sql.get_all_pkgsets_by_hash.format(
            pkghash=self.pkghash
        )
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        if not response:
            self._store_error(
                {"message": f"No data not found in database", "args": self.args},
                self.ll.INFO,
                404,
            )
            return self.error

        res = sort_branches([el[0] for el in response])

        res = {"pkghash": str(self.pkghash), "length": len(res), "branches": res}
        return res, 200


class LastBranchPackages(APIWorker):
    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sitesql
        super().__init__()

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        self.validation_results = []

        if self.args["packager"] == "":
            self.validation_results.append(
                f"packager's nickname should not be empty string"
            )

        if self.args["branch"] == "" or self.args["branch"] not in lut.known_branches:
            self.validation_results.append(
                f"unknown package set name : {self.args['branch']}"
            )
            self.validation_results.append(
                f"allowed package set names are : {lut.known_branches}"
            )

        if self.args["packages_limit"] and self.args["packages_limit"] < 1:
            self.validation_results.append(
                f"last packages limit should be greater or equal to 1"
            )

        if self.validation_results != []:
            return False
        else:
            return True

    def get(self):
        self.branch = self.args["branch"]
        self.packager = self.args["packager"]
        self.packages_limit = self.args["packages_limit"]

        if self.packager is not None:
            packager_sub = f"AND pkg_packager_email LIKE '{self.packager}@%'"
        else:
            self.packager = ""
            packager_sub = ""

        # get source packages diff from current branch state and previous one
        self.conn.request_line = self.sql.get_last_branch_src_diff.format(branch=self.branch)
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        if not response:
            self._store_error(
                {
                    "message": f"No data found in database for given parameters",
                    "args": self.args,
                },
                self.ll.INFO,
                404,
            )
        src_pkg_hashes = [el[0] for el in response]
        # strore list of source package hashes to temporary table
        # create temporary table for source package hashes
        tmp_table = "tmp_srcpkg_hashes"
        self.conn.request_line = self.sql.create_tmp_table.format(
            tmp_table=tmp_table, columns="(pkg_hash UInt64)"
        )
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        # insert package hashes into temporary table
        self.conn.request_line = (
            self.sql.insert_into_tmp_table.format(tmp_table=tmp_table),
            ((x,) for x in src_pkg_hashes),
        )
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        # get source and binary packages info by hashes from temporary table
        self.conn.request_line = self.sql.get_last_branch_pkgs_info.format(
            tmp_table=tmp_table,
            packager=packager_sub,
            limit=self.packages_limit
        )
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        if not response:
            self._store_error(
                {
                    "message": f"No data found in database for packages",
                    "args": self.args,
                },
                self.ll.INFO,
                404,
            )
            return self.error

        PkgMeta = namedtuple(
            "PkgMeta",
            [
                "pkg_name",
                "pkg_version",
                "pkg_release",
                "pkg_summary",
                "changelog_name",
                "changelog_date",
                "changelog_text",
                "hash",
                "pkg_buildtime",
            ],
        )

        packages = (PkgMeta(*el[1:])._asdict() for el in response)

        retval = []

        for pkg in packages:
            pkg["changelog_date"] = datetime_to_iso(pkg["changelog_date"])
            pkg["changelog_nickname"] = get_nickname_from_packager(pkg["changelog_name"])
            retval.append(pkg)

        res = {
            "request_args": self.args,
            "length": len(retval),
            "packages": retval,
        }
        return res, 200
