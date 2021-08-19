from flask_restx import reqparse


package_info_args = reqparse.RequestParser()
package_info_args.add_argument(
    'branch',
    type=str,
    required=True,
    help='name of packageset',
    location='args'
)
package_info_args.add_argument(
    'changelog_last',
    type=int,
    default=3,
    required=False,
    help='changelog history length',
    location='args'
)

pkgset_packages_args = reqparse.RequestParser()
pkgset_packages_args.add_argument(
    'branch',
    type=str,
    required=True,
    help='name of packageset',
    location='args'
)
pkgset_packages_args.add_argument(
    'package_type',
    type=str,
    choices=('all', 'source', 'binary'),
    default='source',
    required=False,
    help='packages type [source|binary|all]',
    location='args'
)
pkgset_packages_args.add_argument(
    'group',
    type=str,
    required=False,
    help='package category',
    location='args'
)
pkgset_packages_args.add_argument(
    'buildtime',
    type=int,
    default=0,
    required=False,
    help='package buildtime',
    location='args'
)

package_chlog_args = reqparse.RequestParser()
package_chlog_args.add_argument(
    'changelog_last',
    type=int,
    default=1,
    required=False,
    help='changelog history length',
    location='args'
)

pkgset_pkghash_args = reqparse.RequestParser()
pkgset_pkghash_args.add_argument(
    'branch',
    type=str,
    required=True,
    help='name of packageset',
    location='args'
)
pkgset_pkghash_args.add_argument(
    'name',
    type=str,
    required=True,
    help='package name',
    location='args'
)

task_by_name_args = reqparse.RequestParser()
task_by_name_args.add_argument(
    'name',
    type=str,
    required=True,
    help='package name',
    location='args'
)

pkgs_by_name_args = reqparse.RequestParser()
pkgs_by_name_args.add_argument(
    'name',
    type=str,
    required=True,
    help='package name',
    location='args'
)
pkgs_by_name_args.add_argument(
    'branch',
    type=str,
    required=False,
    help='name of packageset',
    location='args'
)
pkgs_by_name_args.add_argument(
    'arch',
    type=str,
    required=False,
    help='arch of binary packages',
    location='args'
)

task_last_pkgs_args = reqparse.RequestParser()
task_last_pkgs_args.add_argument(
    'branch',
    type=str,
    required=True,
    help='name of packageset',
    location='args'
)
task_last_pkgs_args.add_argument(
    'timedelta',
    type=int,
    default=864000,
    required=True,
    help='time range from newest task in seconds',
    location='args'
)

pkgset_categories_args = reqparse.RequestParser()
pkgset_categories_args.add_argument(
    'branch',
    type=str,
    required=True,
    help='name of packageset',
    location='args'
)
pkgset_categories_args.add_argument(
    'package_type',
    type=str,
    choices=('all', 'source', 'binary'),
    default='source',
    required=False,
    help='packages type [source|binary|all]',
    location='args'
)

all_archs_args = reqparse.RequestParser()
all_archs_args.add_argument(
    'branch',
    type=str,
    required=True,
    help='name of packageset',
    location='args'
)

all_maintainers_args = reqparse.RequestParser()
all_maintainers_args.add_argument(
    'branch',
    type=str,
    required=True,
    help='name of packageset',
    location='args'
)
maintainer_info_args = reqparse.RequestParser()
maintainer_info_args.add_argument(
    'maintainer_nickname',
    type=str,
    required=True,
    help='nickname of maintainer',
    location='args'
)
maintainer_info_args.add_argument(
    'branch',
    type=str,
    required=True,
    help='name of packageset',
    location='args'
)


maintainer_branches_args = reqparse.RequestParser()
maintainer_branches_args.add_argument(
    'maintainer_nickname',
    type=str,
    required=True,
    help='nickname of maintainer',
    location='args'
)