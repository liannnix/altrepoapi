from api.base import parser

package_name = parser.register_item(
    "package_name",
    type=str,
    required=True,
    help="source or binary package name",
    location="args",
)
package_type_opt = parser.register_item(
    "package_type",
    type=str,
    choices=("source", "binary"),
    default="source",
    required=False,
    help="packages type [source|binary]",
    location="args",
)
maintainer_nickname = parser.register_item(
    "maintainer_nickname",
    type=str,
    required=True,
    help="maintainer nickname",
    location="args",
)

package_bugzilla_args = parser.build_parser(package_name, package_type_opt)
maintainer_bugzilla_args = parser.build_parser(maintainer_nickname)
