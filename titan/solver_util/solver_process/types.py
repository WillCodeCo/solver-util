import enum

class CommandId(enum.Enum):
    SOLVE_PATH = 0
    SOLVE_SUBTREE = 1
    CANCEL = 2
    PING = 3

class SolverState(enum.Enum):
    UNKNOWN = 1
    INITIALIZING = 2
    READY = 3
    SOLVING = 4
    CANCELLING = 5
    CLOSING = 6
    CLOSED = 7


class SolverConfig:
    pass

class SolverProcessException(Exception):
    pass