class SqlRequestError(Exception):
    def __init__(self, value):
        self.dErrorArguments = value
        super().__init__(self, "SQL request error occured")
