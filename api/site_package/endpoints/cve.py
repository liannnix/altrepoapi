from collections import namedtuple

from utils import datetime_to_iso

from api.base import APIWorker
from api.misc import lut
from ..sql import sql


class LastPackagesWithCVEFix(APIWorker):
    """Retrieves information about last packages with CVE's in changelog."""

    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sql
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
