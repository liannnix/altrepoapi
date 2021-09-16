import hashlib
import base64
from collections import namedtuple

from settings import namespace
from utils import get_logger

logger = get_logger(__name__)

AuthCheckResult = namedtuple("AuthCheckResult", ["verified", "error", "value"])

def check_auth(token):
    try:
        token = token.split()[1].strip()
        user, password = base64.b64decode(token).decode("utf-8").split(':')
        passwd_hash = hashlib.sha512(password.encode("utf-8")).hexdigest()
        
        logger.info(f"User '{user}' attempt to authorize")

        if user == namespace.ADMIN_USER and passwd_hash == namespace.ADMIN_PASSWORD:
            logger.info(f"User '{user}' successfully authorized")
            return AuthCheckResult(True, "OK", {"user": user})
        else:
            logger.warning(f"User '{user}' authorization failed")
            return AuthCheckResult(False, "authorization failed", {})
    except:
        logger.error(f"Authorization token validation error")
        return AuthCheckResult(False, "token validation error", {})
