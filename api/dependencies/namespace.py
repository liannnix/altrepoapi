from flask_restx import Namespace

namespace = Namespace("dependencies", description="dependencies information API")

def get_namespace():
    return namespace
