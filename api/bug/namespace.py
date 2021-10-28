from flask_restx import Namespace

namespace = Namespace("bug", description="bug information API")

def get_namespace():
    return namespace
