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
from typing import List, Dict, Tuple, Set

watch_total = Stopwatch()

City = collections.namedtuple("City", "roads, sectors, pop")


def generate(manual_seed: int = None) -> City:
    """ Generates a City with the given seed, or a random seed """
    watch_total.reset()
    watch_total.start()

    roads.Segment.seg_id = 0
    if manual_seed is not None:
        seed = manual_seed
    elif config.ROAD_SEED != 0:
        seed = config.ROAD_SEED
    else:
        seed = time.process_time()
    random.seed(seed)
    pop_seed = (random.randrange(-1, 1) * 1000000000,
                random.randrange(-1, 1) * 1000000000)

    print("Generating {} segments with seed: {}".format(config.MAX_SEGS, seed))

    road_queue = roads.Queue()
    road_queue.push(roads.Segment((0, 0), (config.HIGHWAY_LENGTH, 0), True))

    city = City([], {}, population.Heatmap(pop_seed))

    while not road_queue.is_empty() and len(city.roads) <= config.MAX_SEGS:
        seg = road_queue.pop()

        if local_constraints(seg, city):  
            seg.connect_links()

            city.roads.append(seg)
            sectors.add(seg, city.sectors)

            new_segments = global_goals(seg, city.pop)
            for new_seg in new_segments:
                new_seg.t += seg.t + 1
                road_queue.push(new_seg)

    watch_total.stop()
    print("Time spent (ms): {}".format(watch_total.passed_ms()))

    return city


def highway_deviation() -> int:
    """ Generates a random angle deviation in degrees for a highway """
    return random.randint(-config.HIGHWAY_MAX_ANGLE_DEV,
                          config.HIGHWAY_MAX_ANGLE_DEV)


def branch_deviation() -> int:
    """ Generates a random angle deviation in degrees for a branch """
    return random.randint(-config.BRANCH_MAX_ANGLE_DEV,
                          config.BRANCH_MAX_ANGLE_DEV)


def global_goals(previous_segment: roads.Segment,
                 heatmap: 'population.Heatmap') -> List[roads.Segment]:
    """
    Takes a road that has been placed in the city, and generates new roads
        (branches & extensions) from it
    :param previous_segment: Road to generate continuations from.
        Assumed to already be settled
    :param heatmap: The population heatmap object to base road generation on
    :return: a list of the newly generated roads
    """
    new_segments = []

    if previous_segment.has_snapped != SnapType.No:
        return new_segments

    straight_seg = previous_segment.make_extension(0)
    straight_pop = heatmap.at_line(straight_seg)

    # Extend the current highway, tending towards higher populations
    if previous_segment.is_highway:
        wiggle_seg = previous_segment.make_extension(highway_deviation())
        wiggle_pop = heatmap.at_line(wiggle_seg)

        if wiggle_pop > straight_pop:
            new_segments.append(wiggle_seg)
            next_pop = wiggle_pop
        else:
            new_segments.append(straight_seg)
            next_pop = straight_pop

        if (next_pop > config.HIGHWAY_BRANCH_POP
                and random.random() < config.HIGHWAY_BRANCH_CHANCE):
            angle = (90 * random.randrange(-1, 2, 2)) + branch_deviation()
            branch = previous_segment.make_continuation(config.HIGHWAY_LENGTH,
                                                        angle,
                                                        True,
                                                        True)
            new_segments.append(branch)
    # Always create a street extension if this is a street
    elif straight_pop > random.uniform(0, config.STREET_EXTEND_POP):
        new_segments.append(straight_seg)

    # Sometimes create a street branch, delaying branches from highways
    if (straight_pop > random.uniform(0, config.STREET_BRANCH_POP)
            and random.random() < config.STREET_BRANCH_CHANCE):
        angle = (90 * random.randrange(-1, 2, 2)) + branch_deviation()
        delay = 5 if previous_segment.is_highway else 0
        branch = previous_segment.make_continuation(config.STREET_LENGTH,
                                                    angle,
                                                    False,
                                                    True,
                                                    delay)
        new_segments.append(branch)

    for seg in new_segments:
        seg.parent = previous_segment

    return new_segments


def local_constraints(inspect_seg: roads.Segment, city: City) -> bool:
    """
    Checks that the given segment can either be placed into the city or can be
    modified to fit into the city, returning false if it can't.
    """

    action = None
    last_snap = SnapType.No
    last_inter_factor = 1
    last_ext_factor = 999

    if inspect_seg.parent is not None:
        if is_road_crowding(inspect_seg, inspect_seg.parent.links_e):
            return False

    check_roads = []

    for containing_sector in sectors.from_seg(inspect_seg):
        check_roads += city.sectors.get(containing_sector, [])

    for line in check_roads:
        inter = inspect_seg.find_intersect(line)

        # If the segment intersects with another road
        if (last_snap <= SnapType.Cross
                and inter is not None
                and 0 < inter.main_factor < last_inter_factor):
            last_inter_factor = inter.main_factor
            last_snap = SnapType.Cross

            def action(other_seg=line, crossing=inter) -> bool:
                return snap_to_cross(inspect_seg, other_seg, crossing, city)
        # If the segment's end is near an existing road vertex
        if last_snap <= SnapType.End:
            if (vectors.distance(inspect_seg.end, line.end)
                    < config.SNAP_VERTEX_RADIUS):
                def action(other_seg=line) -> bool:
                    return snap_to_vert(inspect_seg, other_seg, True, False)
                last_snap = SnapType.End
            elif (vectors.distance(inspect_seg.end, line.start)
                    < config.SNAP_VERTEX_RADIUS):
                def action(other_seg=line) -> bool:
                    return snap_to_vert(inspect_seg, other_seg, False, False)
                last_snap = SnapType.End
        # If the segment can be extended to intersect with another road
        if (last_snap <= SnapType.Extend
                and inter is not None
                and 1 < inter.main_factor < last_ext_factor
                and vectors.distance(inspect_seg.end, inter.point)
                < config.SNAP_EXTEND_RADIUS):
            last_ext_factor = inter.main_factor

            def action(other_seg=line, crossing=inter) -> bool:
                return snap_to_cross(inspect_seg, other_seg, crossing, city)
            last_snap = SnapType.Extend

    if action is not None:
        return action()
    return True


def is_road_crowding(inspect_seg: roads.Segment, to_check: Set[roads.Segment]):
    """
    Determines if the given segment forms an angle less than the minimum
    angle difference with any road in to_check
    """
    for road in to_check:
        if road is not inspect_seg:
            if roads.angle_between(inspect_seg, road) < config.MIN_ANGLE_DIFF:
                return True

    return False


def snap_to_cross(mod_road: roads.Segment, other_road: roads.Segment,
                  crossing: roads.Intersection, city: City) -> bool:
    """
    Snaps the mod_road to the given intersection point and splits the other
    road at the intersection if the intersection wouldn't create an almost
    zero-length road, or an angle less than the minimum angle difference
    :param mod_road: The road that is being snapped to an intersection it has
    with other_road
    :param other_road: The road to be split at its intersection with mod_road
    :param crossing: The point where the two roads intersect
    :param city: The city to add the halves of the split other_road to
    :return: True if mod_road can be placed in the city
    """
    angle_diff = roads.angle_between(mod_road, other_road)
    min_diff = min(angle_diff, math.fabs(angle_diff - 180))
    if min_diff < config.MIN_ANGLE_DIFF:
        return False

    # Fail if the crossing would produce a (nearly) zero-length road
    if round(crossing.main_factor, 5) == 0:
        return False
    if round(crossing.main_factor, 5) == 1:
        round_factor = round(crossing.other_factor, 5)
        if round_factor == 0 or round_factor == 1:
            return snap_to_vert(mod_road, other_road, round_factor == 1, True)
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

    city.roads.append(split_half)
    sectors.add(split_half, city.sectors)

    mod_road.links_e.add(other_road)
    mod_road.links_e.add(split_half)
    mod_road.end = crossing[0]

    if crossing.main_factor > 1:
        mod_road.has_snapped = SnapType.Extend
    else:
        mod_road.has_snapped = SnapType.Cross
    return True


def snap_to_vert(mod_road: roads.Segment, other_road: roads.Segment, end: bool,
                 too_close: bool) -> bool:
    """
    Snaps the mod_road's end to an existing intersection at the start or
    the end of other_road
    :param mod_road: The road to modify
    :param other_road: The road to snap mod_road to
    :param end: If mod_road should snap to other_road's end rather than start
    :param too_close: If the snap is happening because a crossing would create
    too small of a road
    :return: True if mod_road can be placed in the city
    """
    if end:
        linking_point = other_road.end
        examine_links = other_road.links_e
    else:
        linking_point = other_road.start
        examine_links = other_road.links_s

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
