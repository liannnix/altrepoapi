from flask_restx import Namespace

namespace = Namespace("site", description="web site API")

def get_namespace():
    return namespace
