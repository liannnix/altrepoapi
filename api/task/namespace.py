from flask_restx import Namespace

namespace = Namespace("task", description="Task's information API")

def get_namespace():
    return namespace
