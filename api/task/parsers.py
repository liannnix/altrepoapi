from flask_restx import reqparse, inputs

task_info_args = reqparse.RequestParser()
task_info_args.add_argument(
    'try',
    type=int,
    required=False,
    help='task try',
    location='args'
)
task_info_args.add_argument(
    'iteration',
    type=int,
    required=False,
    help='task iteration',
    location='args'
)

task_repo_args = reqparse.RequestParser()
task_repo_args.add_argument(
    'include_task_packages',
    type=bool,
    required=False,
    default=False,
    help='include task packages in repository state',
    location='args'
)

task_build_dep_args = reqparse.RequestParser()
task_build_dep_args.add_argument(
    'arch',
    type=str,
    action='split',
    required=False,
    help='list of packages architectures',
    location='args'
)
task_build_dep_args.add_argument(
    'leaf',
    type=str,
    required=False,
    help='assembly dependency chain package',
    location='args'
)
task_build_dep_args.add_argument(
    'depth',
    type=int,
    default=1,
    required=False,
    help='dependency depth',
    location='args'
)
task_build_dep_args.add_argument(
    'dptype',
    type=str,
    choices=('both', 'source', 'binary'),
    default='both',
    required=False,
    help='dependency type [source|binary|both]',
    location='args'
)
task_build_dep_args.add_argument(
    'filter_by_package',
    type=str,
    action='split',
    required=False,
    help='filter result by dependency on binary packages',
    location='args'
)
task_build_dep_args.add_argument(
    'filter_by_source',
    type=str,
    # action='split',
    required=False,
    help='filter result by dependency on source package',
    location='args'
)
task_build_dep_args.add_argument(
    'finite_package',
    type=inputs.boolean,
    default=False,
    required=False,
    help='topological tree leaves packages',
    location='args'
)

task_misconflict_args = reqparse.RequestParser()
task_misconflict_args.add_argument(
    'archs',
    type=str,
    action='split',
    required=False,
    help='list of packages architectures',
    location='args'
)

task_find_pkgset_args = reqparse.RequestParser()
task_find_pkgset_args.add_argument(
    'branches',
    type=str,
    action='split',
    required=False,
    help='list of package sets to filter result',
    location='args'
)

task_buid_dep_set_args = reqparse.RequestParser()
task_buid_dep_set_args.add_argument(
    'archs',
    type=str,
    action='split',
    required=False,
    help='list of packages architectures',
    location='args'
)
