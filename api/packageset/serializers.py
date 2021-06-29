from flask_restx import fields

from api.packageset.packageset import ns

pkgset_compare_model = ns.model('PackagesetCompareModel', {

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
