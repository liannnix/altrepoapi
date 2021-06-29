from flask_restx import reqparse, inputs

pkgset_compare_args = reqparse.RequestParser()
pkgset_compare_args.add_argument(
    'branch',
    type=str,
    required=True,
    help='name of packageset',
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
    default='all',
    required=False,
    help='packages type [source|binary|all]',
    location='args'
)
pkgset_packages_args.add_argument(
    'archs',
    type=str,
    action='split',
    required=False,
    help='list of package architectures',
    location='args'
)
