from collections import namedtuple

from api.base import APIWorker
from database.bug_sql import bugsql
from utils import tuplelist_to_dict


class Bugzilla(APIWorker):

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = bugsql
        super().__init__()

    def check_params_maintainer(self):
        self.logger.debug(f"args : {self.args}")
        self.validation_results = []

        if self.args["maintainer_nickname"] == "":
            self.validation_results.append(
                f"maintainer nickname should not be empty string"
            )

        if self.validation_results != []:
            return False
        else:
            return True

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        self.validation_results = []

        if self.args["srcpkg_name"] == "":
            self.validation_results.append(
                f"Name source package should not be empty string"
            )

        if self.validation_results != []:
            return False
        else:
            return True

    def get_bug_by_package(self):
        srcpkg_name = self.args["srcpkg_name"]
        self.conn.request_line = self.sql.get_pkg_name_by_srcpkg.format(srcpkg_name=srcpkg_name)
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        if not response or response[0][0] == []:
            self._store_error(
                {
                    "message": f"No data found in database for {srcpkg_name}",
                    "args": self.args,
                },
                self.ll.INFO,
                404,
            )
            return self.error
        packages = [el[0] for el in response]
        packages.append(srcpkg_name)
        packages_regex = [f"^{el}$" for el in packages]
        self.conn.request_line = self.sql.get_bugzilla_info_by_srcpkg.format(packages=packages_regex)
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        if not response or response[0][0] == []:
            self._store_error(
                {
                    "message": f"No data found in database for {srcpkg_name}",
                    "args": self.args,
                },
                self.ll.INFO,
                404,
            )
            return self.error

        BugzillaInfo = namedtuple(
            "BugzillaInfoModel",
            [
                "id",
                "status",
                "resolution",
                "severity",
                "product",
                "component",
                "assignee",
                "reporter",
                "summary",
            ],
        )

        res = [BugzillaInfo(el[0], *el[1])._asdict() for el in response]
        res = {"request_args": self.args, "length": len(res), "bugs": res}

        return res, 200

    def get_bug_by_maintainer(self):
        maintainer_nickname = self.args["maintainer_nickname"]
        self.conn.request_line = self.sql.get_bugzilla_info_by_maintainer.format(maintainer_nickname=maintainer_nickname)
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        if not response or response[0][0] == []:
            self._store_error(
                {
                    "message": f"No data found in database for {maintainer_nickname}",
                    "args": self.args,
                },
                self.ll.INFO,
                404,
            )
            return self.error

        BugzillaInfo = namedtuple(
            "BugzillaInfoModel",
            [
                "id",
                "status",
                "resolution",
                "severity",
                "product",
                "component",
                "assignee",
                "reporter",
                "summary",
            ],
        )
        res = [BugzillaInfo(el[0], *el[1])._asdict() for el in response]
        res = {"request_args": self.args, "length": len(res), "bugs": res}

        return res, 200