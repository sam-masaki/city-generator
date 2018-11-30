from enum import IntEnum, auto


class SnapType(IntEnum):
    No = auto()
    Extend = auto()
    End = auto()
    Cross = auto()

    CrossTooClose = auto()
    Split = auto()
    DebugDeleted = auto()
    Shorten = auto()
