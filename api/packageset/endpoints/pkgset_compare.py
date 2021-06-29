from collections import namedtuple

from settings import namespace as settings
from utils import get_logger, build_sql_error_response, logger_level as ll
from utils import tuplelist_to_dict

from api.misc import lut
from database.packageset_sql import pkgsetsql

logger = get_logger(__name__)


class PackagesetCompare:
    pass
