from werkzeug.exceptions import Unauthorized, Forbidden

class ApiUnauthorized(Unauthorized):
    """Raise status code 401 with customizable WWW-Authenticate header."""

    def __init__(
        self,
        description="Unauthorized",
        admin_only=False,
        error=None,
        error_description=None,
    ):
        self.description = description
        self.admin_only = admin_only
        self.error = error
        self.error_description = error_description
        Unauthorized.__init__(
            self, description=description, response=None, www_authenticate=None
        )


class ApiForbidden(Forbidden):
    """Raise status code 403 with WWW-Authenticate header."""

    description = "You are not an administrator"
