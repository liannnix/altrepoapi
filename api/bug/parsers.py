from flask_restx import reqparse

package_bugzilla_args = reqparse.RequestParser()
package_bugzilla_args.add_argument(
    "srcpkg_name",
    type=str,
    required=True,
    help="name source package",
    location="args",
)

maintainer_bugzilla_args = reqparse.RequestParser()
maintainer_bugzilla_args.add_argument(
    "maintainer_nickname",
    type=str,
    required=True,
    help="nickname of maintainer",
    location="args",
)