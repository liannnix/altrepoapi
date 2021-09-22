from flask_restx import Api

from .task.task import ns as task_ns
from .package.package import ns as package_ns
from .packageset.packageset import ns as packageset_ns
from .site.site import ns as site_ns
from .bug.bug import ns as bug_ns


authorizations = {
    'BasicAuth': {
        'type': 'basic',
        'in': 'header',
        'name': 'Authorization'
    }
}

api = Api(
    version="1.2",
    title="altrepodb",
    description="altrepodb API",
    default="api",
    default_label="basic functions",
    authorizations=authorizations
)

api.add_namespace(task_ns)
api.add_namespace(package_ns)
api.add_namespace(packageset_ns)
api.add_namespace(bug_ns)
api.add_namespace(site_ns)
