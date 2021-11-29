from flask_restx import Namespace

namespace = Namespace("export", description="export API")

def get_namespace():
    return namespace
