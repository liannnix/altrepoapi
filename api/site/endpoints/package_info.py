from collections import namedtuple

from utils import datetime_to_iso, tuplelist_to_dict, sort_branches

from api.base import APIWorker
from api.misc import lut
from database.site_sql import sitesql


class PackageChangelog(APIWorker):
    def __init__(self, connection, pkghash, **kwargs):
        self.pkghash = pkghash
        self.conn = connection
        self.args = kwargs
        self.sql = sitesql
        super().__init__()

    def check_params(self):
        self.logger.debug(f"args : {self.args}")
        self.validation_results = []

        if self.args['changelog_last'] < 1:
            self.validation_results.append(f"changelog history length should be not less than 1")

        if self.validation_results != []:
            return False
        else:
            return True

    def get(self):
        self.chlog_length = self.args['changelog_last']
        self.conn.request_line = self.sql.get_pkg_changelog.format(pkghash=self.pkghash)
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        if not response:
            self._store_error(
                {"message": f"No packages found in last packages with hash {self.pkghash}",
                "args": self.args},
                self.ll.INFO,
                404
            )
            return self.error

        changelog_list = []
        for changelog in response[0]:
            i = 0
            for v in changelog:
                changelog_dict = {}
                changelog_dict['date']    = datetime_to_iso(v[0])
                changelog_dict['name']    = v[1]
                changelog_dict['evr']     = v[2]
                changelog_dict['message'] = v[3]
                changelog_list.append(changelog_dict)
                i += 1
                if i >= self.chlog_length:
                    break

        res = {
                'pkghash': str(self.pkghash),
                'request_args' : self.args,
                'length': len(changelog_list),
                'changelog': changelog_list
            }

        return res, 200


class PackageInfo(APIWorker):
    def __init__(self, connection, pkghash, **kwargs):
        self.pkghash = pkghash
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

        if self.args['changelog_last'] < 1:
            self.validation_results.append(f"changelog history length should be not less than 1")

        if self.validation_results != []:
            return False
        else:
            return True

    def get(self):
        self.branch = self.args['branch']
        self.chlog_length = self.args['changelog_last']
        PkgMeta = namedtuple('PkgMeta', [
            'name', 'version', 'release', 'buildtime', 'url', 'license', 
            'summary', 'description', 'packager', 'packager_email', 'category'
        ])
        # get package info
        self.conn.request_line = self.sql.get_pkg_info.format(pkghash=self.pkghash)
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        if not response:
            self._store_error(
                {"message": f"No packages found in last packages with hash {self.pkghash}",
                "args": self.args},
                self.ll.INFO,
                404
            )
            return self.error
        pkg_info = PkgMeta(*response[0])._asdict()
        # get package task
        pkg_task = 0
        pkg_subtask = 0
        self.conn.request_line = self.sql.get_pkg_task_by_hash.format(pkghash=self.pkghash)
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        if response:
            pkg_task = response[0][0]
            pkg_subtask = response[0][1]
        # get package git
        pkg_gear = ''
        self.conn.request_line = self.sql.get_task_gears_by_id.format(
            task=pkg_task,
            subtask=pkg_subtask
        )
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        if response:
            subtask = response[0]
            if subtask[0] == 'gear':
                pkg_gear = lut.gitalt_base + subtask[1]
            elif subtask[0] in ('srpm', 'rebuild'):
                pkg_gear = '/'.join(
                    (lut.gitalt_base, 'srpms', subtask[2][:1], (subtask[2] + '.git'))
                ) 
            elif subtask[0] == 'copy':
                pkg_gear = 'copy from ' + subtask[3]
            elif subtask[0] == 'unknown':
                if subtask[1] != '':
                    pkg_gear = lut.gitalt_base + subtask[1]
                elif subtask[2] != '':
                    pkg_gear = '/'.join(
                        (lut.gitalt_base, 'srpms', subtask[2][:1], (subtask[2] + '.git'))
                    )
            else:
                pass
        # get package maintaners
        pkg_maintainers = []
        self.conn.request_line = self.sql.get_pkg_maintaners.format(
            name=pkg_info['name']
        )
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        pkg_maintainers = [{'name': _[0], 'email': _[1]} for _ in response]
        # get package ACLs
        pkg_acl = []
        self.conn.request_line = self.sql.get_pkg_acl.format(
            name=pkg_info['name'],
            branch=self.branch
        )
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        if response:
            pkg_acl = response[0][0]
        # get package versions
        pkg_versions = []
        self.conn.request_line = self.sql.get_pkg_versions.format(
            name=pkg_info['name']
        )
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        PkgVersions = namedtuple('PkgVersions', ['branch', 'version', 'release', 'pkghash'])
        # sort package versions by branch
        pkg_branches = sort_branches([el[0] for el in response])
        pkg_versions = tuplelist_to_dict(response, 3)
        pkg_versions = [PkgVersions(*(b, *pkg_versions[b]))._asdict() for b in pkg_branches]
        # get provided binary packages
        bin_packages_list = []
        self.conn.request_line = self.sql.get_binary_pkgs.format(pkghash=self.pkghash)
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        bin_packages_list = [_[0] for _ in response]
        # get package changelog
        self.conn.request_line = self.sql.get_pkg_changelog.format(pkghash=self.pkghash)
        status, response = self.conn.send_request()
        if not status:
            self._store_sql_error(response, self.ll.ERROR, 500)
            return self.error
        if not response:
            self._store_error(
                {"message": f"No packages found in last packages with hash {self.pkghash}",
                "args": self.args},
                self.ll.INFO,
                404
            )
            return self.error

        changelog_list = []
        for changelog in response[0]:
            i = 0
            for v in changelog:
                changelog_dict = {}
                changelog_dict['date']    = datetime_to_iso(v[0])
                changelog_dict['name']    = v[1]
                changelog_dict['evr']     = v[2]
                changelog_dict['message'] = v[3]
                changelog_list.append(changelog_dict)
                i += 1
                if i >= self.chlog_length:
                    break

        res = {
                'pkghash': str(self.pkghash),
                'request_args' : self.args,
                **pkg_info,
                'task': pkg_task,
                'gear': pkg_gear,
                'packages': bin_packages_list,
                'changelog': changelog_list,
                'maintainers': pkg_maintainers,
                'acl': pkg_acl,
                'versions': pkg_versions
            }

        return res, 200


class AllPackageArchs(APIWorker):
    def __init__(self, connection, **kwargs):
        self.conn = connection
        self.args = kwargs
        self.sql = sitesql
        super().__init__()

    def get_archs(self):
        self.conn.request_line = self.sql.get_all_bin_pkg_archs
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

        archs = sorted([_ for _ in response[0][0] if _ not in ('x86_64-i586',)])
        res = [_ for _ in archs if _.startswith('x')]
        res += [_ for _ in archs if _.startswith('i')]
        res += [_ for _ in archs if _.startswith('n')]
        res += sorted([_ for _ in archs if _ not in res])

        res = [{'arch': _, 'count': 0} for _ in res]

        res = {
                'length': len(res),
                'archs': res
            }
        return res, 200

    def get_archs_with_src_count(self):
        self.conn.request_line = self.sql.get_all_src_cnt_by_bin_archs
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

        archs = sorted([(*el,) for el in response], key=lambda val: val[1], reverse=True)
        res = [{'arch': _[0], 'count': _[1]} for _ in archs]

        res = {
                'length': len(res),
                'archs': res
            }
        return res, 200
