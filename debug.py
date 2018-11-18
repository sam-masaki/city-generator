import enum


class RoadViews(enum.Enum):
    No = enum.auto()
    Snaps = enum.auto()
    Branches = enum.auto()


SHOW_INFO = True
SHOW_ROAD_VIEW = RoadViews.No
SHOW_ROAD_ORDER = False
SHOW_HEATMAP = False
SHOW_SECTORS = False
SHOW_ISOLATE_SECTOR = False
