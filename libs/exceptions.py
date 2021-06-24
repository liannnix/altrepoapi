class SqlRequestError(Exception):
    def __init__(self, value):
        super().__init__(self, "SQL request error occured")
        self.dErrorArguments = value
