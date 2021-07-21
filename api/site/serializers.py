from flask_restx import fields

from api.site.site import ns

package_info_changelog_el_model = ns.model('SitePackageInfoChangelogElementModel', {
    'date': fields.String(description='changelog date'),
    'name': fields.String(description='changelog name'),
    'evr': fields.String(description='changelog EVR'),
    'message': fields.String(description='changelog message')
})
package_maintaners_el_model = ns.model('SitePackageInfoMaintainersElementModel', {
    'name': fields.String(description='maintainer name'),
    'email': fields.String(description='maintainer email')
})
package_versions_el_model= ns.model('SitePackageVersionsElementModel', {
    'branch': fields.String(description='package set name'),
    'version': fields.String(description='package version'),
    'release': fields.String(description='package release'),
    'pkghash': fields.String(description='package hash UInt64 as string')
})
package_info_model = ns.model('SitePackageInfoModel',{
    'pkghash': fields.String(description='package hash UInt64 as string'),
    'request_args': fields.Raw(description='request arguments'),
    'name': fields.String(description='package name'),
    'version': fields.String(description='package version'),
    'release': fields.String(description='package release'),
    'buildtime': fields.Integer(description='package build time'),
    'task': fields.Integer(description='package build task'),
    'license': fields.String(description='package license'),
    'category': fields.String(description='package group'),
    'url': fields.String(description='package url'),
    'summary': fields.String(description='package summary'),
    'description': fields.String(description='package description'),
    'packager': fields.String(description='package packager name'),
    'packager_email': fields.String(description='package packager email'),
    'packages': fields.List(fields.String, description='bunary packages'),
    'acl': fields.List(fields.String, description='bunary packages'),
    'changelog': fields.Nested(
        package_info_changelog_el_model,
        as_list=True,
        description='package changelog'
    ),
    'maintainers': fields.Nested(
        package_maintaners_el_model,
        as_list=True,
        description='all package maintainers'
    ),
    'versions': fields.Nested(
        package_versions_el_model,
        as_list=True,
        description='all package versions'
    )
})

pkgset_packages_el_model = ns.model('SitePackagesElementModel', {
    'hash': fields.String(description='package hash UInt64 as string'),
    'name': fields.String(description='package name'),
    'version': fields.String(description='package version'),
    'release': fields.String(description='package release'),
    'summary': fields.String(description='package summary'),
    'buildtime': fields.Integer(description='package buildtime'),
    'category': fields.String(description='package category'),
    'maintainer': fields.String(description='package maintainer'),
    'changelog': fields.String(description='package last changelog message'),
})
pkgset_packages_model = ns.model('SitePackagesModel', {
    'request_args': fields.Raw(description='request arguments'),
    'length': fields.Integer(description='number of packages found'),
    'packages': fields.Nested(
        pkgset_packages_el_model,
        description='unpackaged directories information',
        as_list=True
    )
})

package_chlog_el_model = ns.model('SiteChangelogElementModel', {
    'date': fields.String(description='changelog date'),
    'name': fields.String(description='changelog name'),
    'evr': fields.String(description='changelog EVR'),
    'message': fields.String(description='changelog message')
})
package_chlog_model = ns.model('SiteChangelogModel', {
    'pkghash': fields.String(description='package hash UInt64 as string'),
    'request_args': fields.Raw(description='request arguments'),
    'length': fields.Integer(description='number changelog records'),
    'changelog': fields.Nested(
        package_chlog_el_model,
        description='package changelog',
        as_list=True
    )
})

pkgset_pkghash_model = ns.model('SitePackagesetPackageHashModel', {
    'request_args': fields.Raw(description='request arguments'),
    'pkghash': fields.String(description='package hash UInt64 as string')
})


task_by_name_pkg_model = ns.model('SiteTaskByNamePackageModel', {
    'type': fields.String(description='subtask type [gear|package]'),
    'name': fields.String(description='package name or git link')
})
task_by_name_task_model = ns.model('SiteTaskByNameTaskModel', {
    'id': fields.Integer(description='task id'),
    'state': fields.String(description='task state'),
    'branch': fields.String(description='task branch'),
    'owner': fields.String(description='task owner nickname'),
    'packages': fields.Nested(
        task_by_name_pkg_model,
        description='task packages',
        as_list=True
    )
})
task_by_name_model = ns.model('SiteTaskByNameModel', {
    'request_args': fields.Raw(description='request arguments'),
    'length': fields.Integer(description='number of tasks found'),
    'tasks': fields.Nested(
        task_by_name_task_model,
        description='tasks list',
        as_list=True
    )
})
