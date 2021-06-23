from flask_restx import reqparse, inputs

package_info_args = reqparse.RequestParser()
# package_info_args.add_argument(
#     'pkg_hash',
#     type=int,
#     required=False,
#     help='package hash',
#     location='args'
# )

pkg_build_dep_args = reqparse.RequestParser()
pkg_build_dep_args.add_argument(
    'package',
    type=str,
    action='split',
    required=True,
    help='package or list of packages',
    location='args'
)
pkg_build_dep_args.add_argument(
    'branch',
    type=str,
    required=True,
    help='name of packageset',
    location='args'
)
pkg_build_dep_args.add_argument(
    'arch',
    type=str,
    action='split',
    required=False,
    help='list of packages architectures',
    location='args'
)
pkg_build_dep_args.add_argument(
    'leaf',
    type=str,
    required=False,
    help='assembly dependency chain package',
    location='args'
)
pkg_build_dep_args.add_argument(
    'depth',
    type=int,
    default=1,
    required=False,
    help='dependency depth',
    location='args'
)
pkg_build_dep_args.add_argument(
    'dptype',
    type=str,
    default='both',
    required=False,
    help='dependency type [source|binary|both]',
    location='args'
)
pkg_build_dep_args.add_argument(
    'filter_by_package',
    type=str,
    action='split',
    required=False,
    help='filter result by dependency on binary packages',
    location='args'
)
pkg_build_dep_args.add_argument(
    'filter_by_source',
    type=str,
    # action='split',
    required=False,
    help='filter result by dependency on source package',
    location='args'
)
pkg_build_dep_args.add_argument(
    'finite_package',
    type=inputs.boolean,
    default=False,
    required=False,
    help='topological tree leaves packages',
    location='args'
)
