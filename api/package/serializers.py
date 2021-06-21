from flask_restx import fields
from api.restplus import api

package_info_model = api.model('PackageInfoPackageModel',{
    'name': fields.String(description='package name'),
    'version': fields.String(description='package version'),
    'release': fields.String(description='package release'),
    'filename': fields.String(description='package file name')
})
