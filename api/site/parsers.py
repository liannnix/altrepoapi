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
