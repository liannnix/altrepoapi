from flask_restx import reqparse, inputs

package_info_args = reqparse.RequestParser()
package_info_args.add_argument(
    'sha1',
    type=str,
    required=False,
    help='package SHA1 checksum',
    location='args'
)
package_info_args.add_argument(
    'name',
    type=str,
    required=False,
    help='package name',
    location='args'
)
package_info_args.add_argument(
    'version',
    type=str,
    required=False,
    help='package version',
    location='args'
)
package_info_args.add_argument(
    'release',
    type=str,
    required=False,
    help='package release',
    location='args'
)
package_info_args.add_argument(
    'arch',
    type=str,
    required=False,
    help='package arch',
    location='args'
)
package_info_args.add_argument(
    'disttag',
    type=str,
    required=False,
    help='package disttag',
    location='args'
)
package_info_args.add_argument(
    'source',
    type=inputs.boolean,
    default=False,
    required=False,
    help='is source package',
    location='args'
)
package_info_args.add_argument(
    'packager',
    type=str,
    required=False,
    help='package packager name',
    location='args'
)
package_info_args.add_argument(
    'packager_email',
    type=str,
    required=False,
    help='package packager email',
    location='args'
)
package_info_args.add_argument(
    'branch',
    type=str,
    required=False,
    help='name of packageset',
    location='args'
)
package_info_args.add_argument(
    'full',
    type=inputs.boolean,
    default=False,
    required=False,
    help='show full package information',
    location='args'
)


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

misconflict_pkg_args = reqparse.RequestParser()
misconflict_pkg_args.add_argument(
    'packages',
    type=str,
    action='split',
    required=True,
    help='package or list of packages',
    location='args'
)
misconflict_pkg_args.add_argument(
    'branch',
    type=str,
    required=True,
    help='name of packageset',
    location='args'
)
misconflict_pkg_args.add_argument(
    'archs',
    type=str,
    action='split',
    required=False,
    help='list of packages architectures',
    location='args'
)

pkg_find_pkgset_args = reqparse.RequestParser()
pkg_find_pkgset_args.add_argument(
    'packages',
    type=str,
    action='split',
    required=True,
    help='package or list of packages',
    location='args'
)
pkg_find_pkgset_args.add_argument(
    'branches',
    type=str,
    action='split',
    required=False,
    help='list of package sets to filter result',
    location='args'
)
