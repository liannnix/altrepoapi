from flask_restx import Namespace

namespace = Namespace("package", description="Packages information API")

def get_namespace():
    return namespace
