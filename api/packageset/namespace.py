from flask_restx import Namespace

namespace = Namespace("packageset", description="Packageset information API")

def get_namespace():
    return namespace
