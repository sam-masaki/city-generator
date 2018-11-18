import enum


class DebugRoadViews(enum.Enum):
    No = enum.auto()
    Snaps = enum.auto()
    Branches = enum.auto()


DEBUG_INFO = True
DEBUG_ROAD_VIEW = DebugRoadViews.No
DEBUG_ROAD_ORDER = False
DEBUG_HEATMAP = False
DEBUG_SECTORS = False
DEBUG_ISOLATE_SECTOR = False
