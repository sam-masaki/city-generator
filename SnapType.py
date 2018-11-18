import enum


class SnapType(enum.Enum):
    No = 0
    Cross = 1
    End = 2
    Extend = 3
    CrossTooClose = 4
    Split = 5
    DebugDeleted = 6
    Shorten = 7
