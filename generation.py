from Stopwatch import Stopwatch
import roads
import time
import random
from config import *
import population
from SnapType import SnapType
import sectors
import vectors
import math


watch_total = Stopwatch()


def generate(manual_seed=None):

    watch_total.start()

    roads.Segment.seg_id = 0
    global ROAD_SEED
    if manual_seed is None:
        ROAD_SEED = time.process_time()
    else:
        ROAD_SEED = manual_seed
    print("Generating {} segments with seed: {}".format(MAX_SEGS, ROAD_SEED))
    random.seed(ROAD_SEED)

    road_queue = roads.Queue()
    road_queue.push(roads.Segment((0, 0), (HIGHWAY_LENGTH, 0), True))

    segments = []
    sector_segments = {}

    loop_count = 0
    while not road_queue.is_empty() and len(segments) <= MAX_SEGS:
        seg = road_queue.pop()

        if local_constraints(seg, segments, sector_segments):
            seg.insertion_order = loop_count
            seg.connect_links()
            segments.append(seg)
            sectors.add(seg, sector_segments)

            new_segments = global_goals(seg)

            for new_seg in new_segments:
                new_seg.t = seg.t + 1 + new_seg.t
                road_queue.push(new_seg)
        loop_count += 1

    watch_total.stop()
    print("Time spent (ms): {}".format(watch_total.passed_ms()))

    return segments, sector_segments


def highway_deviation():
    return random.randint(-1 * HIGHWAY_MAX_ANGLE_DEV, HIGHWAY_MAX_ANGLE_DEV)


def branch_deviation():
    return random.randint(-1 * BRANCH_MAX_ANGLE_DEV, BRANCH_MAX_ANGLE_DEV)


def global_goals(previous_segment: roads.Segment):
    new_segments = []

    if previous_segment.has_snapped != SnapType.No:
        return new_segments

    straight_seg = previous_segment.make_continuation(previous_segment.length(),
                                                      0,
                                                      previous_segment.is_highway,
                                                      False)
    straight_pop = population.at_line(straight_seg)

    if previous_segment.is_highway:
        wiggle_seg = previous_segment.make_continuation(HIGHWAY_LENGTH,
                                                        highway_deviation(),
                                                        True,
                                                        False)
        wiggle_pop = population.at_line(wiggle_seg)

        if wiggle_pop > straight_pop:
            new_segments.append(wiggle_seg)
            ext_pop = wiggle_pop
        else:
            new_segments.append(straight_seg)
            ext_pop = straight_pop

        if ext_pop > HIGHWAY_BRANCH_POP and random.random() < HIGHWAY_BRANCH_CHANCE:
            sign = random.randrange(-1, 2, 2)
            branch = previous_segment.make_continuation(HIGHWAY_LENGTH,
                                                        (90 * sign) + branch_deviation(),
                                                        True,
                                                        True)
            new_segments.append(branch)

    if straight_pop > STREET_EXTEND_POP:
        if not previous_segment.is_highway:
            new_segments.append(straight_seg)

    if straight_pop > STREET_BRANCH_POP:
        if random.random() < STREET_BRANCH_CHANCE:
            sign = random.randrange(-1, 2, 2)
            delay = 5 if previous_segment.is_highway else 0
            branch = previous_segment.make_continuation(STREET_LENGTH,
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

    priority = 0
    action = None
    last_inter_t = 1
    last_ext_t = 999

    # watch_local_overlap.start()
    if not check_overlap(inspect_seg):
        return False
    # watch_local_overlap.stop()

    road_sectors = sectors.from_seg(inspect_seg)
    for sec in road_sectors:
        if sec not in sector_segments:
            continue
        for line in sector_segments[sec]:
            # watch_local_cross.start()
            inter = inspect_seg.find_intersect(line)
            if inter is not None and 0 < inter[1] < last_inter_t and priority <= 4:
                last_inter_t = inter[1]
                priority = 4

                action = lambda _, line=line, inter=inter: snap_to_cross(inspect_seg, segments, sector_segments, line, inter, False)
                # ????consider finding nearby roads and delete if too similar
            # watch_local_cross.stop()

            # watch_local_vert.start()
            if vectors.distance(line.end, inspect_seg.end) < SNAP_VERTEX_RADIUS and priority <= 3:
                priority = 3

                action = lambda _, line=line: snap_to_vert(inspect_seg, line, True, False)
            # watch_local_vert.stop()

            if inter is not None and 1 < inter[1] < last_ext_t and priority <= 2:
                if vectors.distance(inspect_seg.end, inspect_seg.point_at(inter[1])) < SNAP_EXTEND_RADIUS:
                    last_ext_t = inter[1]
                    point = inter[0]

                    action = lambda _, line=line, inter=inter: snap_to_cross(inspect_seg, segments, sector_segments, line, inter, True)
                    priority = 2

    # watch_local.stop()

    if action is not None:
        return action(None)
    return True


def check_overlap(inspect_seg):
    # This part doesn't have false positives, but it does miss some lines it should catch
    if inspect_seg.parent is not None:
        for road in inspect_seg.parent.links_e:
            if road is not inspect_seg:
                if road.start == inspect_seg.start:
                    angle = road.dir()
                elif road.end == inspect_seg.start:
                    angle = road.dir() - 180
                    if angle < 0:
                        angle += 360
                else: # I think this is ok in this case, because inspect_seg hasn't been settled yet, so you don't know if its links are actually solid
                    continue

                if angle_between(inspect_seg.dir(), angle) < MIN_ANGLE_DIFF:
                    #inspect_seg.has_snapped = SnapType.DebugDeleted
                    return False
    return True


def snap_to_cross(mod_road, all_segments, sector_segments, other_road: roads.Segment, crossing, is_extend):
    aa = angle_between(mod_road.dir(), other_road.dir())
    angle_diff = min(aa, math.fabs(aa - 180))
    if angle_diff < MIN_ANGLE_DIFF:
        return False

    # @FIX Crossings that are really close to existing intersections shouldn't happen; in that case, snap_to_end should
    # take precedence unless doing so causes a new intersection, then it should go back to intersecting. The main issue
    # is how to do that without wasting a ton of calculations, since this seems to happen a fair amount (at least the
    # crossing is too close part). Dividing the full list of segments into sectors could make that recalculation be ok
    if crossing[2] < 0.05:
        return snap_to_vert(mod_road, other_road, False, True)
    elif crossing[2] > 0.95:
        return snap_to_vert(mod_road, other_road, True, True)
    else:
        start_links = other_road.links_s
        start_loc = other_road.start
        old_parent = other_road.parent

        other_road.links_s = set()
        other_road.start = crossing[0]

        if old_parent is not None:
            old_parent.links_e.remove(other_road)
            for road in old_parent.links_e:
                if road.start == old_parent.end:
                    road.links_s.remove(other_road)
                elif road.end == old_parent.end:
                    road.links_e.remove(other_road)

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

    if angle_between(mod_road.dir(), other_angle) < MIN_ANGLE_DIFF:
        return False

    for road in examine_links:
        if road.end == linking_point:
            angle = road.dir()
        elif road.start == linking_point:
            angle = road.dir() - 180
            if angle < 0:
                angle += 360

        if angle_between(mod_road.dir(), angle) < MIN_ANGLE_DIFF:
            return False

    mod_road.end = linking_point

    mod_road.links_e.update(examine_links)
    mod_road.links_e.add(other_road)

    if too_close:
        mod_road.has_snapped = SnapType.CrossTooClose
    else:
        mod_road.has_snapped = SnapType.End
    return True


def angle_between(a1, a2):
    while a1 < 0:
        a1 += 360
    while a2 < 0:
        a2 += 360

    reg = math.fabs(a1 - a2)
    res = min(reg, math.fabs(reg - 360))

    return res
