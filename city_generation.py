import pygame
import heapq
import math
import random
import time
from heapdict import heapdict
from noise import snoise2
import enum
from config import *
from RoadSegment import *
from Stopwatch import Stopwatch
from SnapType import SnapType

from vector_operations import *
from typing import List, Tuple, Optional


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

DEBUG_NEW_FEATURE = False

NOISE_SEED = (0, 0)

seed = time.process_time()
random.seed(seed)


class RoadQueue:
    def __init__(self):
        self.heap = []

    def push(self, segment):
        heapq.heappush(self.heap, segment)

    def pop(self):
        return heapq.heappop(self.heap)

    def is_empty(self):
        return self.heap == []


def world_to_screen(world_pos, pan, zoom):
    result = ((world_pos[0] * zoom) + pan[0],
              (world_pos[1] * zoom) + pan[1])
    return result


def screen_to_world(screen_pos, pan, zoom):
    result = (((screen_pos[0] - pan[0]) / zoom),
              ((screen_pos[1] - pan[1]) / zoom))
    return result


def draw_all_roads(roads, screen, pan, zoom):
    for road in roads:
        width = 2
        color = (255, 255, 255)

        if road.is_highway:
            width = 4
            color = (255, 0, 0)
        elif DEBUG_ROAD_VIEW == DebugRoadViews.Snaps:
            if road.has_snapped == SnapType.Cross:
                color = (255, 100, 100)
            elif road.has_snapped == SnapType.End:
                color = (100, 255, 100)
            elif road.has_snapped == SnapType.Extend:
                color = (100, 100, 255)
            elif road.has_snapped == SnapType.CrossTooClose:
                color = (100, 255, 255)
        elif DEBUG_ROAD_VIEW == DebugRoadViews.Branches:
            if road.is_branch:
                color = (100, 255, 100)
        if road.has_snapped == SnapType.DebugDeleted:
            color = (0, 255, 0)

        draw_road(road, color, width, screen, pan, zoom)


def draw_roads_selected(selection, screen, pan, zoom):
    if selection is not None:
        draw_road(selection[0], (255, 255, 0), 8, screen, pan, zoom)

        for road in selection[1]:
            draw_road(road, (0, 255, 0), 6, screen, pan, zoom)


def draw_roads_path(path, searched, start, end, screen, pan, zoom):
    if len(searched) != 0:
        width = 5
        color = (255, 0, 255)

        for road in searched:
            draw_road(road, color, width, screen, pan, zoom)

    if len(path) != 0:
        width = 7
        color = (0, 255, 255)
        for road in path:
            draw_road(road, color, width, screen, pan, zoom)

    width = 8
    if start is not None:
        draw_road(start, (0, 255, 0), width, screen, pan, zoom)
    if end is not None:
        draw_road(end, (255, 0, 0), width, screen, pan, zoom)


def draw_road(road, color, width, screen, pan, zoom):
    pygame.draw.line(screen, color, world_to_screen(road.start, pan, zoom),
                     world_to_screen(road.end, pan, zoom), width)


def select_nearby_road(world_pos: Tuple[float, float], roads: List[RoadSegment]) -> RoadSegment:
    closest: Tuple[RoadSegment, float] = (None, 9999)
    for road in roads:
        dist = dist_vectors(world_pos, road.point_at(0.5))
        if dist < closest[1]:
            closest = (road, dist)
    if closest[1] < 100:
        selected = closest[0]

        return selected

    return None


def draw_heatmap(screen: pygame.Surface, square_size, pan, zoom):
    x_max = math.ceil(screen.get_width() / square_size) + 1
    y_max = math.ceil(screen.get_height() / square_size) + 1

    for x in range(0, x_max):
        for y in range(0, y_max):
            screen_point = (x * square_size,
                            y * square_size)
            world_point = screen_to_world(screen_point, pan, zoom)

            intensity = population_point(world_point)
            color = (0, max(min(intensity * 100, 255), 0), 0)

            pos = (screen_point[0] - (square_size / 2), screen_point[1] - (square_size / 2))
            dim = (square_size, square_size)

            pygame.draw.rect(screen, color, pygame.Rect(pos, dim))


def draw_sectors(screen: pygame.Surface, pan, zoom):
    x_min = round(screen_to_world((0, 0), pan, zoom)[0] // SECTOR_SIZE) + 1
    x_max = round(screen_to_world((SCREEN_RES[0], 0), pan, zoom)[0] // SECTOR_SIZE) + 1

    x_range = range(x_min, x_max)
    for x in x_range:
        pos_x = world_to_screen((SECTOR_SIZE * x, 0), pan, zoom)[0]
        pygame.draw.line(screen, (200, 200, 200), (pos_x, 0), (pos_x, SCREEN_RES[1]))

    y_min = round(screen_to_world((0, 0), pan, zoom)[1] // SECTOR_SIZE) + 1
    y_max = round(screen_to_world((0, SCREEN_RES[1]), pan, zoom)[1] // SECTOR_SIZE) + 1

    y_range = range(y_min, y_max)
    for y in y_range:
        pos_y = world_to_screen((0, SECTOR_SIZE * y), pan, zoom)[1]
        pygame.draw.line(screen, (200, 200, 200), (0, pos_y), (SCREEN_RES[0], pos_y))


def zoom_change(prev, increment, center, pan):
    new_step = prev + increment

    old_level = zoom_at(prev)
    new_level = zoom_at(new_step)

    old_world = screen_to_world(center, pan, old_level)
    new_world = screen_to_world(center, pan, new_level)

    world_pan = sub_vectors(new_world, old_world)

    return new_level, world_to_screen(world_pan, (0, 0), new_level)


def zoom_at(step):
    return math.pow((step / 12) + 1, 2)


def path_dijkstra(start, end, all_roads):
    node_queue = heapdict()
    for road in all_roads:
        road.pathing_dist_start = 0 if road is start else 9999999
        road.pathing_prev = None
        node_queue[road] = road.pathing_dist_start

    while not len(node_queue) == 0:
        curr_min = node_queue.popitem()[0]

        if curr_min is end:
            break

        neighbors = curr_min.links_s.union(curr_min.links_e)

        for road in neighbors:
            this_dist = curr_min.pathing_dist_start + road.pathing_cost()
            if this_dist < road.pathing_dist_start:
                road.pathing_dist_start = this_dist
                road.pathing_prev = curr_min
                node_queue[road] = this_dist

    sequence = []
    if end.pathing_prev is not None or end is start:
        curr_node = end
        while curr_node is not None:
            sequence.append(curr_node)
            curr_node = curr_node.pathing_prev

    return sequence


def path_astar(start, end, all_roads):
    closed = []
    open = heapdict()

    for road in all_roads:
        road.pathing_dist_start = 0 if road is start else 9999999
        road.pathing_dist_end = road.pathing_heuristic(end) if road is start else 9999999
        road.pathing_prev = None
    open[start] = start.pathing_dist_end

    while len(open):
        curr_min = open.popitem()[0]
        if curr_min is end:
            break

        closed.append(curr_min)
        neighbors = curr_min.links_s.union(curr_min.links_e)

        for road in neighbors:
            if road in closed:
                continue

            new_dist_start = curr_min.pathing_dist_start + road.pathing_cost()

            if new_dist_start < road.pathing_dist_start:
                road.pathing_dist_start = new_dist_start
                road.pathing_dist_end = road.pathing_dist_start + road.pathing_heuristic(end)
                road.pathing_prev = curr_min
                if road not in open:
                    open[road] = road.pathing_dist_end

    sequence = []
    if end.pathing_prev is not None or end is start:
        curr_node = end
        while curr_node is not None:
            sequence.append(curr_node)
            curr_node = curr_node.pathing_prev

    return sequence, closed


def main():
    pygame.init()

    screen = pygame.display.set_mode(SCREEN_RES)

    running = True

    result = generate()
    roads = result[0]
    sects = result[1]

    path = []
    path_searched = []
    path_start = None
    path_end = None

    selection = None

    zoom_level = 1
    zoom_increment = 0

    prev_mouse = (0, 0)
    drag_start = None
    viewport_pos = (0, 0)
    prev_pressed = (False, False, False)

    gohu_font = pygame.font.SysFont("GohuFont", 11)

    prev_time = pygame.time.get_ticks()

    road_labels = []

    for road in roads:
        road_labels.append((gohu_font.render(str(road.global_id), True, (255, 255, 255)),
                            road.point_at(0.5)))

    while running:
        if pygame.time.get_ticks() - prev_time < 16:
            continue

        prev_time = pygame.time.get_ticks()
        screen.fill((0, 0, 0))
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_g:
                    result = generate()
                    roads = result[0]
                    sects = result[1]
                    road_labels = []

                    for road in roads:
                        road_labels.append((gohu_font.render(str(road.global_id), True, (255, 255, 255)),
                                            road.point_at(0.5)))
                # Debug Views
                elif event.key == pygame.K_1:
                    global DEBUG_INFO
                    DEBUG_INFO = not DEBUG_INFO
                elif event.key == pygame.K_2:
                    global DEBUG_ROAD_VIEW
                    if DEBUG_ROAD_VIEW == DebugRoadViews.No:
                        DEBUG_ROAD_VIEW = DebugRoadViews.Snaps
                    elif DEBUG_ROAD_VIEW == DebugRoadViews.Branches:
                        DEBUG_ROAD_VIEW = DebugRoadViews.No
                    elif DEBUG_ROAD_VIEW == DebugRoadViews.Snaps:
                        DEBUG_ROAD_VIEW = DebugRoadViews.Branches
                elif event.key == pygame.K_3:
                    global DEBUG_ROAD_ORDER
                    DEBUG_ROAD_ORDER = not DEBUG_ROAD_ORDER
                elif event.key == pygame.K_4:
                    global DEBUG_HEATMAP
                    DEBUG_HEATMAP = not DEBUG_HEATMAP
                elif event.key == pygame.K_5:
                    global DEBUG_SECTORS
                    DEBUG_SECTORS = not DEBUG_SECTORS
                elif event.key == pygame.K_6:
                    global DEBUG_ISOLATE_SECTOR
                    DEBUG_ISOLATE_SECTOR = not DEBUG_ISOLATE_SECTOR

                # Pathing
                elif event.key == pygame.K_z:
                    path_start = select_nearby_road(screen_to_world(pygame.mouse.get_pos(), viewport_pos, zoom_level), roads)
                elif event.key == pygame.K_x:
                    path_end = select_nearby_road(screen_to_world(pygame.mouse.get_pos(), viewport_pos, zoom_level), roads)
                elif event.key == pygame.K_c:
                    path_data = path_astar(path_start, path_end, roads)
                    path = path_data[0]
                    path_searched = path_data[1]
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 4:
                    good_var_name = zoom_change(zoom_increment, 1, pygame.mouse.get_pos(), viewport_pos)
                    zoom_level = good_var_name[0]
                    viewport_pos = add_vectors(viewport_pos, good_var_name[1])
                    zoom_increment += 1
                elif event.button == 5:
                    if zoom_increment > -11:
                        good_var_name = zoom_change(zoom_increment, -1, pygame.mouse.get_pos(), viewport_pos)
                        zoom_level = good_var_name[0]
                        viewport_pos = add_vectors(viewport_pos, good_var_name[1])
                        zoom_increment -= 1

        if prev_pressed[0]:
            if pygame.mouse.get_pressed()[0]:
                viewport_pos = add_vectors(viewport_pos, sub_vectors(pygame.mouse.get_pos(), prev_mouse))
                prev_mouse = pygame.mouse.get_pos()
            else:
                if pygame.mouse.get_pos() == drag_start:
                    selected = select_nearby_road(screen_to_world(drag_start, viewport_pos, zoom_level), roads)
                    if selected is not None:
                        start_ids = []
                        end_ids = []
                        connections = []
                        sectors = sectors_from_seg(selected)
                        for road in selected.links_s:
                            start_ids.append(road.global_id)
                            connections.append(road)
                        for road in selected.links_e:
                            end_ids.append(road.global_id)
                            connections.append(road)
                        selection = (selected, connections, start_ids, end_ids, sectors)
                    else:
                        selection = None

                drag_start = None
        else:
            if pygame.mouse.get_pressed()[0]:
                drag_start = pygame.mouse.get_pos()
                prev_mouse = pygame.mouse.get_pos()
        prev_pressed = pygame.mouse.get_pressed()

        if DEBUG_HEATMAP:
            draw_heatmap(screen, 50, viewport_pos, zoom_level)

        if DEBUG_SECTORS:
            draw_sectors(screen, viewport_pos, zoom_level)

        if DEBUG_ISOLATE_SECTOR and selection is not None:
            draw_all_roads(sects[sector_at(selection[0].point_at(0.5))], screen, viewport_pos, zoom_level)
        else:
            tl_sect = sector_at(screen_to_world((0, 0), viewport_pos, zoom_level))
            br_sect = sector_at(screen_to_world(SCREEN_RES, viewport_pos, zoom_level))
            for x in range(tl_sect[0], br_sect[0] + 1):
                for y in range(tl_sect[1], br_sect[1] + 1):
                    if (x, y) in sects:
                        draw_all_roads(sects[(x, y)], screen, viewport_pos, zoom_level)
        draw_roads_selected(selection, screen, viewport_pos, zoom_level)
        draw_roads_path(path, path_searched, path_start, path_end, screen, viewport_pos, zoom_level)

        if DEBUG_INFO:
            debug_labels_left = []
            debug_labels_right = []

            mouse_pos = pygame.mouse.get_pos()

            debug_labels_left.append("Pointer (screen): {}".format(str(mouse_pos)))
            debug_labels_left.append("    (world): {}".format(screen_to_world(mouse_pos, viewport_pos, zoom_level)))
            debug_labels_left.append("    pop_at: {}".format(population_point(screen_to_world(pygame.mouse.get_pos(), viewport_pos, zoom_level))))
            debug_labels_left.append("    sec_at: {}".format(sector_at(screen_to_world(pygame.mouse.get_pos(), viewport_pos, zoom_level))))
            debug_labels_left.append("Pan: {}".format(viewport_pos))
            debug_labels_left.append("Zoom: {}x".format(str(zoom_level)))

            if selection is not None:
                debug_labels_left.append("Selected: {}".format(str(selection[0].global_id)))
                if selection[0].parent is not None:
                    debug_labels_left.append("    Parent: {}".format(str(selection[0].parent.global_id)))
                else:
                    debug_labels_left.append("    Parent: None")
                debug_labels_left.append("    dir: {}".format(str(selection[0].dir())))
                debug_labels_left.append("    links_s: {}".format(str(selection[2])))
                debug_labels_left.append("    links_e: {}".format(str(selection[3])))
                debug_labels_left.append("    has_snapped: {}".format(str(selection[0].has_snapped)))
                debug_labels_left.append("    sectors: {}".format(str(selection[4])))
            else:
                debug_labels_left.append("Selected: None")

            debug_labels_right.append("Seed: {}".format(str(seed)))

            debug_labels_right.append("# of segments: {}".format(str(MAX_SEGS)))

            height = 10
            for label in debug_labels_left:
                screen.blit(gohu_font.render(label, False, (255, 255, 255), (0, 0, 0)),
                            (10, height))
                height += 15

            height = 10
            for label in debug_labels_right:
                surf = gohu_font.render(label, False, (255, 255, 255))
                screen.blit(surf,
                            (SCREEN_RES[0] - surf.get_width() - 10, height))
                height += 15

        if DEBUG_ROAD_ORDER:
            for label in road_labels:
                label_pos = world_to_screen(label[1], viewport_pos, zoom_level)
                if -20 < label_pos[0] < SCREEN_RES[0] and -20 < label_pos[1] < SCREEN_RES[1]:
                    screen.blit(label[0], label_pos)

        pygame.display.flip()


all_intersections = []


def angle_between(a1, a2):
    while a1 < 0:
        a1 += 360
    while a2 < 0:
        a2 += 360

    reg = math.fabs(a1 - a2)
    res = min(reg, math.fabs(reg - 360))

    return res


def population_level(seg):
    return (population_point(seg.start) + population_point(seg.end)) / 2


def population_point(point):
    x = point[0] + NOISE_SEED[0]
    y = point[1] + NOISE_SEED[1]

    value1 = (snoise2(x/10000, y/10000) + 1) / 2
    value2 = (snoise2((x/20000) + 500, (y/20000) + 500) + 1) / 2
    value3 = (snoise2((x/20000) + 1000, (y/20000) + 1000) + 1) / 2
    return math.pow(((value1 * value2) + value3), 2)


watch_local = Stopwatch()
watch_local_overlap = Stopwatch()
watch_local_cross = Stopwatch()
watch_local_vert = Stopwatch()
watch_total = Stopwatch()


def generate(manual_seed=None):
    watch_local.reset()
    watch_local_overlap.reset()
    watch_local_cross.reset()
    watch_local_vert.reset()
    watch_total.reset()

    watch_total.start()

    RoadSegment.seg_id = 0
    global seed
    if manual_seed is None:
        seed = time.process_time()
    else:
        seed = manual_seed

    print("Generating {} segments with seed: {}".format(seed, MAX_SEGS))

    random.seed(seed)

    global all_intersections
    all_intersections = []

    road_queue = RoadQueue()
    road_queue.push(RoadSegment((0, 0), (HIGHWAY_LENGTH, 0), True))

    segments = []
    sector_segments = {}

    loop_count = 0
    while not road_queue.is_empty() and len(segments) <= MAX_SEGS:
        seg = road_queue.pop()

        if local_constraints(seg, segments, sector_segments):
            seg.insertion_order = loop_count
            seg.connect_links()
            segments.append(seg)
            add_to_sector(seg, sector_segments)

            new_segments = global_goals(seg)

            for new_seg in new_segments:
                new_seg.t = seg.t + 1 + new_seg.t
                road_queue.push(new_seg)
        loop_count += 1

    watch_total.stop()
    print("Time spent total: {}\n"
          "    local constraints: {}, number of runs: {}\n"
          "        overlap calc: {}, per calc (ns): {}\n"
          "        cross calc: {}, per calc (ns): {}\n"
          "        vert calc: {}, per calc (ns): {}".format(watch_total.passed_ms(),
                                                            watch_local.passed_ms(), watch_local.num_runs,
                                                            watch_local_overlap.passed_ms(), watch_local_overlap.avg_ns(),
                                                            watch_local_cross.passed_ms(), watch_local_cross.avg_ns(),
                                                            watch_local_vert.passed_ms(), watch_local_vert.avg_ns()))

    return segments, sector_segments


def add_to_sector(new_seg, sectors):
    containing_sectors = sectors_from_seg(new_seg)

    for sector in containing_sectors:
        if sector not in sectors:
            sectors[sector] = []
        sectors[sector].append(new_seg)


def sectors_from_seg(segment: RoadSegment):
    all_sectors = set()

    # this could be made variable depending on whether a road is only in one sector, or overlaps NSEW, or overlaps diag
    # and also it depends on the maximum possible road length
    # also this whole thing is in dire need of optimizing, but whatever
    start_sector = sector_at(segment.start)
    end_sector = sector_at(segment.end)

    all_sectors.add(start_sector)
    all_sectors.add(end_sector)

    edge_dist = MIN_DIST_EDGE_CONTAINED if start_sector == end_sector else MIN_DIST_EDGE_CROSS

    start_secs = sectors_from_point(segment.start, edge_dist)
    end_secs = sectors_from_point(segment.end, edge_dist)

    return start_secs.union(end_secs)


def sector_at(point):
    return int(point[0] // SECTOR_SIZE), int(point[1] // SECTOR_SIZE)


def sectors_from_point(point, distance):
    start_sector = sector_at(point)
    
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


def highway_deviation():
    return random.randint(-1 * HIGHWAY_MAX_ANGLE_DEV, HIGHWAY_MAX_ANGLE_DEV)


def branch_deviation():
    return random.randint(-1 * BRANCH_MAX_ANGLE_DEV, BRANCH_MAX_ANGLE_DEV)


def global_goals(previous_segment: RoadSegment):
    new_segments = []

    if previous_segment.has_snapped != SnapType.No:
        return new_segments

    straight_seg = previous_segment.make_continuation(previous_segment.length(),
                                                      0,
                                                      previous_segment.is_highway,
                                                      False)
    straight_pop = population_level(straight_seg)

    if previous_segment.is_highway:
        wiggle_seg = previous_segment.make_continuation(HIGHWAY_LENGTH,
                                                        highway_deviation(),
                                                        True,
                                                        False)
        wiggle_pop = population_level(wiggle_seg)

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

    road_sectors = sectors_from_seg(inspect_seg)
    for sec in road_sectors:
        if sec not in sector_segments:
            continue
        for line in sector_segments[sec]:
            # watch_local_cross.start()
            inter = find_intersect(inspect_seg.start, inspect_seg.end, line.start, line.end)
            if inter is not None and 0 < inter[1] < last_inter_t and priority <= 4:
                last_inter_t = inter[1]
                priority = 4

                action = lambda _, line=line, inter=inter: snap_to_cross(inspect_seg, segments, sector_segments, line, inter, False)
                # ????consider finding nearby roads and delete if too similar
            # watch_local_cross.stop()

            # watch_local_vert.start()
            if dist_vectors(line.end, inspect_seg.end) < SNAP_VERTEX_RADIUS and priority <= 3:
                priority = 3

                action = lambda _, line=line: snap_to_vert(inspect_seg, line, True, False)
            # watch_local_vert.stop()

            if inter is not None and 1 < inter[1] < last_ext_t and priority <= 2:
                if dist_vectors(inspect_seg.end, inspect_seg.point_at(inter[1])) < SNAP_EXTEND_RADIUS:
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


def snap_to_cross(mod_road, all_segments, sector_segments, other_road: RoadSegment, crossing, is_extend):
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
        all_intersections.append(crossing[0])

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

        split_half = RoadSegment(start_loc, crossing[0], other_road.is_highway)
        split_half.parent = old_parent
        split_half.links_e.add(other_road)
        split_half.connect_links()
        split_half.is_branch = other_road.is_branch

        other_road.is_branch = False
        other_road.parent = split_half
        other_road.links_s.add(split_half)

        all_segments.append(split_half)
        add_to_sector(split_half, sector_segments)

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


if __name__ == "__main__":
    main()
