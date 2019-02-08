import config
import roads
import vectors
from typing import Dict, Tuple, List, Set


def add(new_seg: roads.Segment, sectors: Dict[Tuple[int, int], List[roads.Segment]]):
    containing_sectors = from_seg(new_seg)

    for sector in containing_sectors:
        if sector not in sectors:
            sectors[sector] = []
        sectors[sector].append(new_seg)


def from_seg(segment: roads.Segment) -> Set[Tuple[int, int]]:
    start_sector = containing_sector(segment.start)
    end_sector = containing_sector(segment.end)

    aux_secs = set()

    if start_sector[0] != end_sector[0] and start_sector[1] != end_sector[1]:
        diff = vectors.sub(start_sector, end_sector)
        aux_secs.add((end_sector[0] + diff[0], end_sector[1]))
        aux_secs.add((end_sector[0], end_sector[1] + diff[1]))

    start_secs = from_point(segment.start, config.MIN_DIST_EDGE_CONTAINED)
    end_secs = from_point(segment.end, config.MIN_DIST_EDGE_CONTAINED)

    return start_secs.union(end_secs).union(aux_secs)


def from_point(point: Tuple[float, float], distance: int) -> Set[Tuple[int, int]]:
    start_sector = containing_sector(point)

    sectors = {start_sector}

    x_mod = 0
    y_mod = 0

    if point[0] % config.SECTOR_SIZE < distance:
        x_mod = -1
    elif config.SECTOR_SIZE - (point[0] % config.SECTOR_SIZE) < distance:
        x_mod = 1

    if point[1] % config.SECTOR_SIZE < distance:
        y_mod = -1
    elif config.SECTOR_SIZE - (point[1] % config.SECTOR_SIZE) < distance:
        y_mod = 1

    sectors.add(vectors.add(start_sector, (x_mod, 0)))
    sectors.add(vectors.add(start_sector, (0, y_mod)))
    sectors.add(vectors.add(start_sector, (x_mod, y_mod)))

    return sectors


def containing_sector(point: Tuple[float, float]) -> Tuple[int, int]:
    return int(point[0] // config.SECTOR_SIZE), int(point[1] // config.SECTOR_SIZE)
