from flask_restx import fields
from api.restplus import api

task_info_model = api.model('TaskInfoModel',{
        'task_id': fields.Integer(description='task id'),
        'subtask_id': fields.Integer(description='subtask id'),
        'subtask_contents': fields.Raw(description='subtask contents')
})

task_repo_package_model = api.model('TaskRepoPackageModel',{
        'name': fields.String(description='package name'),
        'version': fields.String(description='package version'),
        'release': fields.String(description='package release'),
        'filename': fields.String(description='package file name')
})

task_repo_info_model = api.model('TaskRepoInfoModel',{
        'name': fields.String(description='package set name'),
        'date': fields.String(description='package set upload date in ISO8601 format'),
        'tag': fields.String(description='package set upload tag')
})

### FIXME: correctly displayed in Swagger UI but doesn't work with marshalling
task_repo_archs_model = api.model('TaskRepoArchsModel', {
    '*': fields.Nested(task_repo_package_model, as_list=True)
})

task_repo_model = api.model('TaskRepoModel',{
        'task_id': fields.Integer(description='task id'),
        'base_repository': fields.Nested(
            task_repo_info_model,
            description='last uploaded package set used as base'
        ),
        'task_diff_list': fields.List(
            fields.Integer,
            description='list of tasks applied to base package set'
        ),
        'archs': fields.Nested(task_repo_archs_model,
            description='list of packages by architectures'
        )
})
### FIXME: correct for marshalling but wrong displayed in Swagger UI ##
# task_repo_packages = fields.Nested(task_repo_package_model, as_list=True)
# task_repo_packages_wild = fields.Wildcard(task_repo_packages)

# task_repo_archs_model = api.model('TaskRepoArchsModel', {
#     '*': task_repo_packages_wild
# })

# task_repo_model = api.model('TaskRepoModel',{
#         'task_id': fields.Integer(description='task id'),
#         'base_repository': fields.Nested(
#             task_repo_info_model,
#             description='last uploaded package set used as base'
#         ),
#         'task_diff_list': fields.List(
#             fields.Integer,
#             description='list of tasks applied to base package set'
#         ),
#         'archs': fields.Nested(task_repo_archs_model,
#             description='list of packages by architectures'
#         )
### END ###