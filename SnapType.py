from enum import IntEnum, auto


class SnapType(IntEnum):
    # Ordered by priority from low to high
    No = 0
    Extend = 1
    End = 2
    Cross = 3

    # Special SnapTypes, no priority
    CrossTooClose = 10
    Split = 11
    DebugDeleted = 12
    Shorten = 13
