from flask_restx import fields
from api.restplus import api

package_info_model = api.model('PackageInfoPackageModel',{
    'name': fields.String(description='package name'),
    'version': fields.String(description='package version'),
    'release': fields.String(description='package release'),
    'filename': fields.String(description='package file name')
})

pkg_build_dep_el_model = api.model('PackageBuildDependencyElementModel',{
    'name': fields.String(description='package name'),
    'version': fields.String(description='package version'),
    'release': fields.String(description='package release'),
    'epoch': fields.Integer(description='package name'),
    'serial': fields.Integer(attribute='serial_', description='package name'),
    'sourcerpm': fields.String(description='source package file'),
    'branch': fields.String(description='package set name'),
    'buildtime': fields.String(description='package build time'),
    'archs': fields.List(fields.String, description='package archs'),
    'cycle': fields.List(fields.String, description='package cycle dependencies'),
    'requires': fields.List(fields.String, description='package requirements'),
    'acl': fields.List(fields.String, description='package ACL list')
})

pkg_build_dep_model = api.model('PackageBuildDependencyModel',{
    'request_args': fields.Raw(description='request arguments'),
    'length': fields.Integer(description='number of packages found'),
    'dependencies': fields.Nested(pkg_build_dep_el_model,
        description='build dependency results',
        as_list=True
    )
})

misconflict_pkg_model = api.model('PackageMisconflictPackageModel',{
    'input_package': fields.String(description='package name'),
    'conflict_package': fields.String(description='package name'),
    'version': fields.String(description='package version'),
    'release': fields.String(description='package release'),
    'epoch': fields.Integer(description='package name'),
    'archs': fields.List(fields.String, description='package archs'),
    'files_with_conflict': fields.List(fields.String, description='conflict files')
})

misconflict_pkgs_model = api.model('PackageMisconflictPackagesModel',{
    'request_args': fields.Raw(description='request arguments'),
    'length': fields.Integer(description='number of packages found'),
    'conflicts': fields.Nested(misconflict_pkg_model,
        description='conflicts',
        as_list=True
    )
})
