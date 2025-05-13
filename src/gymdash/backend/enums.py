from enum import Enum, IntEnum

class SimStatusCode(IntEnum):
    SUCCESS = 0
    FAIL = 1
    INFO = 2

class SimStatusSubcode(IntEnum):
    NONE = 0
    ERROR = 1
    STOPPED = 2