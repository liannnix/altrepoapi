import base64
from collections import namedtuple

AuthCheckResult = namedtuple("AuthCheckResult", ["verified", "error", "value"])

ADMIN_USER = "admin"
ADMIN_PASSWORD = "12qwaszx"

def check_auth(token):
    try:
        token = token.split()[1].strip()
        user, password = base64.b64decode(token).decode("utf-8").split(':')

        if (user, password) in ((ADMIN_USER, ADMIN_PASSWORD),):
            return AuthCheckResult(True, "OK", {"user": user})
        else:
            return AuthCheckResult(False, "authorization failed", {})
    except:
        return AuthCheckResult(False, "token validation error", {})
