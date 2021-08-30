from flask_restx import fields

from api.package.package import ns

bugzilla_info_el_model = ns.model(
    "BugzillaInfoElementModel",
    {
        "id": fields.String(description="id bugs"),
        "status": fields.String(description="status bugs"),
        "resolution": fields.String(description=""),
        "severity": fields.String(description="severity bugs"),
        "product": fields.String(description="name package"),
        "component": fields.String(description="name branch"),
        "assignee": fields.String(description="bug creator"),
        "reporter": fields.String(description="responsible for the bug"),
        "summary": fields.String(description="summary bugs")
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