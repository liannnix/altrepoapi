from flask_restx import fields

from api.package.package import ns

bugzilla_info_el_model = ns.model(
    "BugzillaInfoElementModel",
    {
        "id": fields.String(description="bug id"),
        "status": fields.String(description="bug status"),
        "resolution": fields.String(description="bug resolution"),
        "severity": fields.String(description="bug severity"),
        "product": fields.String(description="package name"),
        "component": fields.String(description="branch name"),
        "assignee": fields.String(description="bug assigned to"),
        "reporter": fields.String(description="bug registered by"),
        "summary": fields.String(description="bug summary"),
        "updated": fields.String(attribute="ts", description="bug record last changed")
    },
)
bugzilla_info_model = ns.model(
    "BugzillaInfoModel",
    {
        "request_args": fields.Raw(description="request arguments"),
        "length": fields.Integer(description="number of bugs found"),
        "bugs": fields.Nested(
            bugzilla_info_el_model,
            description="bugzilla info",
            as_list=True,
        ),
    },
)
