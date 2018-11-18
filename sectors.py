from config import *
import roads
from typing import Dict, Tuple, List


def add(new_seg, sectors: Dict[Tuple[int, int], List[roads.Segment]]):
    containing_sectors = from_seg(new_seg)

    for sector in containing_sectors:
        if sector not in sectors:
            sectors[sector] = []
        sectors[sector].append(new_seg)


def from_seg(segment: roads.Segment):
    all_sectors = set()

    # this could be made variable depending on whether a road is only in one sector, or overlaps NSEW, or overlaps diag
    # and also it depends on the maximum possible road length
    # also this whole thing is in dire need of optimizing, but whatever
    start_sector = containing_sector(segment.start)
    end_sector = containing_sector(segment.end)

    all_sectors.add(start_sector)
    all_sectors.add(end_sector)

    edge_dist = MIN_DIST_EDGE_CONTAINED if start_sector == end_sector else MIN_DIST_EDGE_CROSS

    start_secs = from_point(segment.start, edge_dist)
    end_secs = from_point(segment.end, edge_dist)

    return start_secs.union(end_secs)


def from_point(point, distance):
    start_sector = containing_sector(point)

    sectors = {start_sector}

    if point[0] % SECTOR_SIZE < distance:
        sectors.add((start_sector[0] - 1, start_sector[1]))
        if point[1] % SECTOR_SIZE < distance:
            sectors.add((start_sector[0] - 1, start_sector[1] - 1))
        elif SECTOR_SIZE - (point[1] % SECTOR_SIZE) < distance:
            sectors.add((start_sector[0] - 1, start_sector[1] + 1))
    elif SECTOR_SIZE - (point[0] % SECTOR_SIZE) < distance:
        sectors.add((start_sector[0] + 1, start_sector[1]))
        if SECTOR_SIZE - (point[1] % SECTOR_SIZE) < distance:
            sectors.add((start_sector[0] + 1, start_sector[1] + 1))
        elif SECTOR_SIZE - (point[1] % SECTOR_SIZE) < distance:
            sectors.add((start_sector[0] + 1, start_sector[1] - 1))
    if point[1] % SECTOR_SIZE < distance:
        sectors.add((start_sector[0], start_sector[1] - 1))
    elif SECTOR_SIZE - (point[1] % SECTOR_SIZE) < distance:
        sectors.add((start_sector[0], start_sector[1] + 1))

    return sectors

def containing_sector(point):
    return int(point[0] // SECTOR_SIZE), int(point[1] // SECTOR_SIZE)
