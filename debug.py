import enum
import collections
import drawing
import population
import sectors
import config

class RoadViews(enum.Enum):
    No = enum.auto()
    Snaps = enum.auto()
    Branches = enum.auto()

Selection = collections.namedtuple("Selection", "road, connections, start_ids, end_ids, selected_sectors")

def labels(screen_data, input_data, path_data, selection):
    mouse_world_pos = drawing.screen_to_world(input_data.pos, screen_data)

    debug_labels_left = []
    debug_labels_right = []

    debug_labels_left.append("Pointer (screen): {}".format(str(input_data.pos)))
    debug_labels_left.append("    (world): {}".format(mouse_world_pos))
    debug_labels_left.append("    pop_at: {}".format(population.at_point(mouse_world_pos)))
    debug_labels_left.append("    sec_at: {}".format(sectors.containing_sector(mouse_world_pos)))
    debug_labels_left.append("Pan: {}".format(screen_data.pan))
    debug_labels_left.append("Zoom: {}x".format(str(screen_data.zoom)))

    if selection is not None:
        debug_labels_left.append("Selected: {}".format(str(selection.road.global_id)))
        if selection.road.parent is not None:
            debug_labels_left.append("    Parent: {}".format(str(selection.road.parent.global_id)))
        else:
            debug_labels_left.append("    Parent: None")
        debug_labels_left.append("    dir: {}".format(str(selection.road.dir())))
        debug_labels_left.append("    links_s: {}".format(str(selection.start_ids)))
        debug_labels_left.append("    links_e: {}".format(str(selection.end_ids)))
        debug_labels_left.append("    has_snapped: {}".format(str(selection.road.has_snapped)))
        debug_labels_left.append("    sectors: {}".format(str(selection.selected_sectors)))
        debug_labels_left.append("    length: {}".format(selection.road.length()))
    else:
        debug_labels_left.append("Selected: None")
    debug_labels_left.append("Path Length: {}".format(path_data.length))

    debug_labels_right.append("Seed: {}".format(str(config.ROAD_SEED)))

    debug_labels_right.append("# of segments: {}".format(str(config.MAX_SEGS)))

    return (debug_labels_left, debug_labels_right)


SHOW_INFO = True
SHOW_ROAD_VIEW = RoadViews.No
SHOW_ROAD_ORDER = False
SHOW_HEATMAP = False
SHOW_SECTORS = False
SHOW_ISOLATE_SECTOR = False
