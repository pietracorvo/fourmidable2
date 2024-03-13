class DangerousValue(Exception):
    """Exception raised when the instrument reading gets to a dangerous value"""

    def __init__(self, msg, data):
        Exception.__init__(self, msg)
        self.data = data
        self.msg = msg


class DangerousTemperature(DangerousValue):
    pass

class ClosingAll(Exception):
    pass

class OutputStop(Exception):
    pass
