from flask_restx import fields

from api.packageset.packageset import ns

pkgset_compare_pkg_model = ns.model('PackagesetComparePackageModel', {
    'name': fields.String(description='package name'),
    'version': fields.String(description='package version'),
    'release': fields.String(description='package release')
})
pkgset_compare_el_model = ns.model('PackagesetCompareElementModel', {
    'pkgset1': fields.String(description='packageset #1 name'),
    'pkgset2': fields.String(description='packageset #2 name'),
    'package1': fields.Nested(
        pkgset_compare_pkg_model,
        description='package from packageset #1'
    ),
    'package2': fields.Nested(
        pkgset_compare_pkg_model,
        description='package from packageset #2'
    ),
})
pkgset_compare_model = ns.model('PackagesetCompareModel', {
    'request_args': fields.Raw(description='request arguments'),
    'length': fields.Integer(description='number of packages found'),
    'packages': fields.Nested(pkgset_compare_el_model,
        description='unpackaged directories information',
        as_list=True
    )
})

pkgset_packages_el_model = ns.model('PackagesetPackagesElementModel', {
    'name': fields.String(description='package name'),
    'version': fields.String(description='package version'),
    'release': fields.String(description='package release'),
    'summary': fields.String(description='package summary'),
    'url': fields.String(description='package url'),
    'license': fields.String(description='package license'),
    'category': fields.String(description='package category'),
    'maintainers': fields.List(fields.String, description='package maintainers'),
    'acl_list': fields.List(fields.String, description='package ACL list'),
    'archs': fields.List(fields.String, description='package archs')
})
pkgset_packages_model = ns.model('PackagesetPackagesModel', {
    'request_args': fields.Raw(description='request arguments'),
    'length': fields.Integer(description='number of packages found'),
    'packages': fields.Nested(pkgset_packages_el_model,
        description='unpackaged directories information',
        as_list=True
    )
})
