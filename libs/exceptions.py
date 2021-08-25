class SqlRequestError(Exception):
    """Custom exception raised on SQL request errors."""

    def __init__(self, value):
        self.error_details: dict = value
        super().__init__(self, "SQL request error occured")
