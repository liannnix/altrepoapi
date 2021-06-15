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

task_repo_archs_model = api.model('TaskRepoArchsModel', {
    'arch': fields.String(description='architecture'),
    'packages': fields.Nested(task_repo_package_model,
        description='packages list',
        as_list=True
    )
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
            description='list of packages by architectures',
            as_list=True
        )
})

task_diff_dependencies_model = api.model('TaskDiffDependenciesModel', {
    'type': fields.String,
    'del': fields.List(fields.String),
    'add': fields.List(fields.String)
})

task_diff_packages_model = api.model('TaskDiffPackagesModel', {
    'package': fields.String,
    'del': fields.List(fields.String),
    'add': fields.List(fields.String),
    'dependencies': fields.Nested(task_diff_dependencies_model, as_list=True) 
})

task_diff_archs_model = api.model('TaskDiffArchsModel', {
    'arch': fields.String,
    'packages': fields.Nested(task_diff_packages_model, as_list=True)
})

task_diff_model = api.model('TaskDiffModel', {
    'task_id': fields.Integer,
    'task_diff': fields.Nested(task_diff_archs_model, as_list=True)
})
