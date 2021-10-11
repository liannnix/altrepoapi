from flask_restx import reqparse

package_bugzilla_args = reqparse.RequestParser()
package_bugzilla_args.add_argument(
    "package_name",
    type=str,
    required=True,
    help="source or binary package name",
    location="args",
)
package_bugzilla_args.add_argument(
    "package_type",
    type=str,
    choices=("source", "binary"),
    default="source",
    required=False,
    help="packages type [source|binary]",
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
