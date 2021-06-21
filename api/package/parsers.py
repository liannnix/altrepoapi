from flask_restx import reqparse

package_info_args = reqparse.RequestParser()
package_info_args.add_argument(
    'pkg_hash',
    type=int,
    required=False,
    help='task try',
    location='args'
)
