from flask_restx import reqparse

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
    'name',
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
