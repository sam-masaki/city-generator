from Stopwatch import Stopwatch
import roads
import time
import random
import config
import population
from SnapType import SnapType
import sectors
import vectors
import math
import collections

watch_total = Stopwatch()

City = collections.namedtuple("City", "roads, sectors")


def generate(manual_seed=None):
    watch_total.reset()
    watch_total.start()

    roads.Segment.seg_id = 0
    if manual_seed is not None:
        seed = manual_seed
    elif config.ROAD_SEED != 0:
        seed = config.ROAD_SEED
    else:
        seed = time.process_time()
    print("Generating {} segments with seed: {}".format(config.MAX_SEGS, seed))
    random.seed(seed)

    road_queue = roads.Queue()
    road_queue.push(roads.Segment((0, 0), (config.HIGHWAY_LENGTH, 0), True))

    road_segments = []
    road_sectors = {}

    while not road_queue.is_empty() and len(road_segments) <= config.MAX_SEGS:
        seg = road_queue.pop()

        if local_constraints(seg, road_segments, road_sectors):
            seg.connect_links()
            road_segments.append(seg)
            sectors.add(seg, road_sectors)

            new_segments = global_goals(seg)

            for new_seg in new_segments:
                new_seg.t += seg.t + 1
                road_queue.push(new_seg)

    watch_total.stop()
    print("Time spent (ms): {}".format(watch_total.passed_ms()))

    return City(road_segments, road_sectors)


def highway_deviation():
    return random.randint(-1 * config.HIGHWAY_MAX_ANGLE_DEV, config.HIGHWAY_MAX_ANGLE_DEV)


def branch_deviation():
    return random.randint(-1 * config.BRANCH_MAX_ANGLE_DEV, config.BRANCH_MAX_ANGLE_DEV)


def global_goals(previous_segment: roads.Segment):
    new_segments = []

    if previous_segment.has_snapped != SnapType.No:
        return new_segments

    straight_seg = previous_segment.make_extension(0)
    straight_pop = population.at_line(straight_seg)

    if previous_segment.is_highway:
        wiggle_seg = previous_segment.make_extension(highway_deviation())
        wiggle_pop = population.at_line(wiggle_seg)

        if wiggle_pop > straight_pop:
            new_segments.append(wiggle_seg)
            ext_pop = wiggle_pop
        else:
            new_segments.append(straight_seg)
            ext_pop = straight_pop

        if ext_pop > config.HIGHWAY_BRANCH_POP and random.random() < config.HIGHWAY_BRANCH_CHANCE:
            sign = random.randrange(-1, 2, 2)
            branch = previous_segment.make_continuation(config.HIGHWAY_LENGTH,
                                                        (90 * sign) + branch_deviation(),
                                                        True,
                                                        True)
            new_segments.append(branch)

    if straight_pop > config.STREET_EXTEND_POP:
        if not previous_segment.is_highway:
            new_segments.append(straight_seg)

    if straight_pop > config.STREET_BRANCH_POP:
        if random.random() < config.STREET_BRANCH_CHANCE:
            sign = random.randrange(-1, 2, 2)
            delay = 5 if previous_segment.is_highway else 0
            branch = previous_segment.make_continuation(config.STREET_LENGTH,
                                                        (90 * sign) + branch_deviation(),
                                                        False,
                                                        True,
                                                        delay)
            new_segments.append(branch)

    for seg in new_segments:
        seg.parent = previous_segment

    return new_segments


def local_constraints(inspect_seg, segments, sector_segments):
    # watch_local.start()

    action = None
    last_snap = SnapType.No
    last_inter_factor = 1
    last_ext_factor = 999

    if inspect_seg.parent is not None:
        if is_road_crowding(inspect_seg, inspect_seg.parent.links_e):
            return False

    road_sectors = sectors.from_seg(inspect_seg)
    for containing_sector in road_sectors:
        if containing_sector not in sector_segments:
            continue
        for line in sector_segments[containing_sector]:
            inter = inspect_seg.find_intersect(line)

            if last_snap <= SnapType.Cross and inter is not None and 0 < inter.main_factor < last_inter_factor:
                last_inter_factor = inter.main_factor
                last_snap = SnapType.Cross

                action = lambda _, line=line, inter=inter: \
                    snap_to_cross(inspect_seg, segments, sector_segments, line, inter, False)

            if last_snap <= SnapType.End and vectors.distance(line.end, inspect_seg.end) < config.SNAP_VERTEX_RADIUS:

                action = lambda _, line=line: \
                    snap_to_vert(inspect_seg, line, True, False)

            if last_snap <= SnapType.Extend and inter is not None and 1 < inter.main_factor < last_ext_factor:
                if vectors.distance(inspect_seg.end, inspect_seg.point_at(inter.main_factor)) < config.SNAP_EXTEND_RADIUS:
                    last_ext_factor = inter.main_factor

                    action = lambda _, line=line, inter=inter: \
                        snap_to_cross(inspect_seg, segments, sector_segments, line, inter, True)
                    last_snap = SnapType.Extend
                    
    if action is not None:
        return action(None)
    return True

# Returns true if the road forms an angle difference < the minimum with any of the roads in to_check
def is_road_crowding(inspect_seg, to_check):
    for road in to_check:
        if road is not inspect_seg:
            if roads.angle_between(inspect_seg, road) < config.MIN_ANGLE_DIFF:
                return True

    return False

def snap_to_cross(mod_road: roads.Segment, all_segments, sector_segments, other_road: roads.Segment, crossing, is_extend):
    angle_diff = roads.angle_between(mod_road, other_road)
    min_diff = min(angle_diff, math.fabs(angle_diff - 180))
    if min_diff < config.MIN_ANGLE_DIFF:
        return False

    # Fail if the crossing would produce a (nearly) zero-length road
    if round(crossing[1], 5) == 0:
        return False
    if round(crossing[1], 5) == 1:
        if round(crossing[2], 5) == 0 or round(crossing[2], 5) == 1:
            return snap_to_vert(mod_road, other_road, round(crossing[2], 5) == 1, True)
    if round(crossing[2], 5) == 0 or round(crossing[2], 5) == 1:
        return False

    start_loc = other_road.start
    old_parent = other_road.parent

    if old_parent is not None:
        old_parent.links_e.remove(other_road)
        for road in old_parent.links_e:
            if road.start == old_parent.end:
                if other_road not in road.links_s:
                    print(other_road.global_id)
                    print(road.global_id)
                road.links_s.remove(other_road)
            elif road.end == old_parent.end:
                road.links_e.remove(other_road)

    other_road.links_s = set()
    other_road.start = crossing[0]

    split_half = roads.Segment(start_loc, crossing[0], other_road.is_highway)
    split_half.parent = old_parent
    split_half.links_e.add(other_road)
    split_half.connect_links()
    split_half.is_branch = other_road.is_branch

    other_road.is_branch = False
    other_road.parent = split_half
    other_road.links_s.add(split_half)

    all_segments.append(split_half)
    sectors.add(split_half, sector_segments)

    mod_road.links_e.add(other_road)
    mod_road.links_e.add(split_half)
    mod_road.end = crossing[0]

    if is_extend:
        mod_road.has_snapped = SnapType.Extend
    else:
        mod_road.has_snapped = SnapType.Cross
    return True


def snap_to_vert(mod_road, other_road, end, too_close):
    if end:
        linking_point = other_road.end
        examine_links = other_road.links_e
        other_angle = other_road.dir()
    else:
        linking_point = other_road.start
        examine_links = other_road.links_s
        other_angle = other_road.dir() - 180
        if other_angle < 0:
            other_angle += 360

    if is_road_crowding(mod_road, examine_links.union({other_road})):
        return False

    mod_road.end = linking_point

    mod_road.links_e.update(examine_links)
    mod_road.links_e.add(other_road)

    if too_close:
        mod_road.has_snapped = SnapType.CrossTooClose
    else:
        mod_road.has_snapped = SnapType.End
    return True