from flask_restx import Api

from .task.task import ns as task_ns
from .package.package import ns as package_ns
from .packageset.packageset import ns as packageset_ns

api = Api(
    version='1.0',
    title='altrepodb',
    description='altrepodb API',
    default='api',
    default_label='basic functions'
)

api.add_namespace(task_ns)
api.add_namespace(package_ns)
api.add_namespace(packageset_ns)
