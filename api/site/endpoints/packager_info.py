from collections import namedtuple

from api.base import APIWorker
from api.misc import lut
from database.site_sql import sitesql
from utils import sort_branches, datetime_to_iso


class AllPackagesetsByHash(APIWorker):
    def __init__(self, connection, pkghash, **kwargs):
        self.pkghash = pkghash
        self.conn = connection
        self.args = kwargs
        self.sql = sitesql
        super().__init__()

    def get(self):
        self.conn.request_line = self.sql.get_all_pkgsets_by_hash.format(pkghash=self.pkghash)
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        if not response:
            self._store_error(
                {"message": f"No data not found in database",
                "args": self.args},
                self.ll.INFO,
                404
            )
            return self.error

        res = sort_branches([_[0] for _ in response])

        res = {
                'pkghash': str(self.pkghash),
                'length': len(res),
                'branches': res
            }
        return res, 200


class AllMaintainers(APIWorker):
    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sitesql
        super().__init__()

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        self.validation_results = []

        if self.args['branch'] == '' or self.args['branch'] not in lut.known_branches:
            self.validation_results.append(f"unknown package set name : {self.args['branch']}")
            self.validation_results.append(f"allowed package set names are : {lut.known_branches}")

        if self.validation_results != []:
            return False
        else:
            return True

    def get_maintainers(self):
        branch = self.args['branch']
        self.conn.request_line = self.sql.get_all_maintainers.format(branch=branch)
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        if not response:
            self._store_error(
                {"message": f"No data not found in database",
                 "args": self.args},
                self.ll.INFO,
                404
            )
            return self.error

        maintainers = sorted([(*el,) for el in response], key=lambda val: val[0])
        res = [{'pkg_packager': _[0], 'pkg_packager_email': _[1],'count_source_pkg': _[2]} for _ in maintainers]

        res = {
            'request_args': self.args,
            'length': len(res),
            'maintainers': res
        }

        return res, 200


class MaintainerInfo(APIWorker):
    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sitesql
        super().__init__()

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        self.validation_results = []

        if self.args['branch'] == '' or self.args['branch'] not in lut.known_branches:
            self.validation_results.append(f"unknown package set name : {self.args['branch']}")
            self.validation_results.append(f"allowed package set names are : {lut.known_branches}")

        if self.args['maintainer_nickname'] == '':
            self.validation_results.append(
                f"maintainer nickname should not be empty string"
            )

        if self.validation_results != []:
            return False
        else:
            return True

    def get_maintainer_info(self):
        maintainer_nickname = self.args['maintainer_nickname']
        branch = self.args['branch']
        self.conn.request_line = self.sql.get_maintainer_info.format(maintainer_nickname=maintainer_nickname, branch=branch)
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        if not response or response[0][0] == []:
            self._store_error(
                {"message": f"No data found in database for {maintainer_nickname} {branch}",
                 "args": self.args},
                self.ll.INFO,
                404
            )
            return self.error

        MaintainersInfo = namedtuple('MaintainersInfoModel', [
            'maintainer_name', 'maintainer_email', 'last_buildtime', 'count_source_pkg',
            'count_binary_pkg'
        ])
        res = MaintainersInfo(*response[0])._asdict()
        res['last_buildtime'] = datetime_to_iso(res['last_buildtime'])
        res = {
            'request_args': self.args,
            'information': res
        }

        return res, 200


class MaintainerPackages(APIWorker):
    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sitesql
        super().__init__()

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        self.validation_results = []

        if self.args['branch'] == '' or self.args['branch'] not in lut.known_branches:
            self.validation_results.append(f"unknown package set name : {self.args['branch']}")
            self.validation_results.append(f"allowed package set names are : {lut.known_branches}")

        if self.args['maintainer_nickname'] == '':
            self.validation_results.append(
                f"maintainer nickname should not be empty string"
            )

        if self.validation_results != []:
            return False
        else:
            return True

    def get_maintainer_packages(self):
        maintainer_nickname = self.args['maintainer_nickname']
        branch = self.args['branch']
        self.conn.request_line = self.sql.get_maintainer_pkg.format(maintainer_nickname=maintainer_nickname,
                                                                    branch=branch)
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        if not response:
            self._store_error(
                {"message": f"No data not found in database",
                 "args": self.args},
                self.ll.INFO,
                404
            )
            return self.error

        MaintainerPackages = namedtuple('MaintainerPackagesModel', [
            'name', 'buildtime', 'url', 'summary', 'version', 'release'
        ])
        res = [MaintainerPackages(*el)._asdict() for el in response]
        res = {
            'request_args': self.args,
            'length': len(res),
            'packages': res
        }

        return res, 200


class MaintainerBranches(APIWorker):
    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sitesql
        super().__init__()

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        self.validation_results = []

        if self.args['maintainer_nickname'] == '':
            self.validation_results.append(
                f"maintainer nickname should not be empty string"
            )

        if self.validation_results != []:
            return False
        else:
            return True

    def get_branches(self):
        maintainer_nickname = self.args['maintainer_nickname']
        self.conn.request_line = self.sql.get_maintainer_branches.format(
            maintainer_nickname=maintainer_nickname
        )
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error

        MaintainerBranches = namedtuple('MaintainerBranches', ['branch', 'count'])
        branches = []
        for branch in sort_branches([el[0] for el in response]):
            for test in [MaintainerBranches(*b)._asdict() for b in response]:
                if test['branch'] == branch:
                    branches.append(test)
                    break
        res = {
            'request_args': self.args,
            'length': len(branches),
            'branches': branches
        }

        return res, 200