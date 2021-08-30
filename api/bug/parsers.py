from flask_restx import reqparse

package_bugzilla_args = reqparse.RequestParser()
package_bugzilla_args.add_argument(
    "srcpkg_name",
    type=str,
    required=True,
    help="source package name",
    location="args",
)

maintainer_bugzilla_args = reqparse.RequestParser()
maintainer_bugzilla_args.add_argument(
    "maintainer_nickname",
    type=str,
    required=True,
    help="maintainer nickname",
    location="args",
)
