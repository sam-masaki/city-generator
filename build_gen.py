import math

import roads


def gen_lots(city):
    searched_right = set()
    searched_left = set()
    result = []

    for seg in city.roads:
        if seg not in searched_left:
            lot = find_lot(seg, acute_left, searched_left,
                           searched_right)
            if lot is not None:
                result.append(lot)
        if seg not in searched_right:
            lot = find_lot(seg, acute_right, searched_right,
                           searched_left)
            if lot is not None:
                result.append(lot)
    return result


def find_lot(segment, angle_main, searched_main, searched_rev):
    if len(segment.links_s) == 0:
        return None

    lot = [segment.start]
    curr = angle_main(segment, segment.links_e)
    if curr is None:
        return None

    main_in_lot = set()
    rev_in_lot = set()

    main_in_lot.add(segment)
    link_at_start = curr.start == segment.end
    while curr is not segment:
        if link_at_start:
            if curr in searched_main:
                return None
            lot.append(curr.start)

            main_in_lot.add(curr)

            next_seg = angle_main(curr, curr.links_e)
            if next_seg is None:
                return None
            link_at_start = next_seg.start == curr.end
        else:
            if curr in searched_rev:
                return None
            lot.append(curr.end)

            rev_in_lot.add(curr)

            next_seg = angle_main(curr, curr.links_s)
            if next_seg is None:
                return None
            link_at_start = next_seg.start == curr.start
        curr = next_seg
    searched_main |= main_in_lot
    searched_rev |= rev_in_lot
    return lot


def acute_right(segment, neighbors):
    min_neighbor = None
    min_angle = 85

    close_neighbor = None
    for neighbor in neighbors:
        diff = roads.angle_between_ccw(segment, neighbor)
        if min_angle <= diff <= 360:
            min_angle = diff
            min_neighbor = neighbor
        #if diff > 179:
        #    close_neighbor = neighbor
    return min_neighbor if min_neighbor is not None else close_neighbor


def acute_left(segment, neighbors):
    max_neighbor = None
    max_angle = 275

    close_neighbor = None
    for neighbor in neighbors:
        diff = roads.angle_between_ccw(segment, neighbor)
        if max_angle >= diff >= 0:
            max_angle = diff
            max_neighbor = neighbor
        #if diff < -179:
        #    close_neighbor = neighbor
    return max_neighbor if max_neighbor is not None else close_neighbor
