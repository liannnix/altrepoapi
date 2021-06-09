from flask_restplus import Api
from settings import namespace
from utils import get_logger

logger = get_logger(__name__)

api = Api(
    version='1.0',
    title='altrepodb',
    description='altrepodb API',
    default='api',
    default_label='basic functions'
)

@api.errorhandler
def default_error_handler(e):
    message = 'An unhandled exception occurred.'
    logger.exception(message)

    if not namespace.FLASK_DEBUG:
        return {'message': message}, 500

# @api.errorhandler(NoResultFound)
# def database_not_found_error_handler(e):
#     """No results found in database"""
#     log.warning(traceback.format_exc())
#     return {'message': 'A database result was required but none was found.'}, 404