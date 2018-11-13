import pygame
import heapq
import math
import random
import time
from heapdict import heapdict
from noise import snoise2
import enum
from config import *

class DebugRoadViews(enum.Enum):
    No = enum.auto()
    Snaps = enum.auto()
    Branches = enum.auto()


class SnapType(enum.Enum):
    No = 0
    Cross = 1
    End = 2
    Extend = 3
    CrossTooClose = 4
    Split = 5
    DebugDeleted = 6
    Shorten = 7


DEBUG_INFO = True
DEBUG_ROAD_VIEW = DebugRoadViews.No
DEBUG_ROAD_ORDER = False
DEBUG_HEATMAP = False

DEBUG_NEW_FEATURE = False

NOISE_SEED = (0, 0)

seed = time.process_time()
random.seed(seed)


def road_from_dir(start, direction, length, is_highway, time_delay):
    end_x = length * math.cos(math.radians(direction))
    end_y = length * math.sin(math.radians(direction))

    seg = RoadSegment(start, (end_x, end_y), is_highway, time_delay)
    return seg


class RoadSegment:
    seg_id = 0

    def __init__(self, start, end, is_highway, time_delay=0):
        self.start = start
        self.end = end
        self.is_highway = is_highway
        self.t = time_delay
        self.has_snapped = SnapType.No
        self.is_branch = False

        self.parent = None
        self.links_s = set()
        self.links_e = set()
        self.settled = False

        self.insertion_order = 0
        self.global_id = RoadSegment.seg_id

        self.pathing_dist_start = 9999999
        self.pathing_dist_end = 9999999
        self.pathing_prev = None

        RoadSegment.seg_id += 1

    def __lt__(self, other):
        return self.t < other.t

    def __gt__(self, other):
        return self.t > other.t

    def copy(self):
        return RoadSegment(self.start, self.end, self.is_highway, self.t)

    def make_continuation(self, length, offset, is_highway, is_branch, delay=0):
        radian_dir = math.radians(self.dir() + offset)

        end_x = self.end[0] + (length * math.cos(radian_dir))
        end_y = self.end[1] + (length * math.sin(radian_dir))

        road = RoadSegment(self.end, (end_x, end_y), is_highway, delay)
        road.is_branch = is_branch

        return road

    def length(self):
        return dist_points(self.start, self.end)

    def dir(self):
        angle = math.degrees(math.atan2(self.end[1] - self.start[1], self.end[0] - self.start[0]))
        if angle < 0:
            angle += 360
        return angle

    def as_rect(self):
        angle = self.dir()
        width = 16 if self.is_highway else 6
        list = []

        point_1 = (self.start[0] + (width * math.cos(math.radians(angle + 90))), self.start[1] + (width * math.sin(math.radians(angle + 90))))
        point_2 = (self.start[0] + (width * math.cos(math.radians(angle - 90))), self.start[1] + (width * math.sin(math.radians(angle - 90))))
        point_3 = (self.end[0] + (width * math.cos(math.radians(angle + 90))), self.end[1] + (width * math.sin(math.radians(angle + 90))))
        point_4 = (self.end[0] + (width * math.cos(math.radians(angle - 90))), self.end[1] + (width * math.sin(math.radians(angle - 90))))

        list.append(point_1)
        list.append(point_2)
        list.append(point_3)
        list.append(point_4)

        return list

    def collides_width(self, other):
        # may not be needed since the tmwhere citygen checks for collision to weed out unneccesary checks, but I think
        # separating into sectors will work better
        return True

    # Assumes that self has a parent, and assumes
    def connect_links(self):
        if self.parent is not None:
            for road in self.parent.links_e:
                if self.start == road.end:
                    road.links_e.add(self)
                elif self.start == road.start:
                    road.links_s.add(self)
                else:
                    print("AAAAAAAAAAAAAAA")

                self.links_s.add(road)
            self.parent.links_e.add(self)
            self.links_s.add(self.parent)

        for road in self.links_e:
            if not road.settled:
                print("Should this happen?")
                continue

            if self.end == road.start:
                road.links_s.add(self)
            elif self.end == road.end:
                road.links_e.add(self)
            else:
                print("OSEANOEMANOMEANOMANOEAMSOENAOMSAOENA")

        self.settled = True

    def pathing_cost(self):
        multiplier = 0.75 if self.is_highway else 1

        return round(self.length() * multiplier * 0.1)

    def pathing_heuristic(self, goal):
        return dist_points(point_on_road(self, 0.5), point_on_road(goal, 0.5)) * 0.1


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


def draw_road(screen, road, selected_road, selected_connections, path, start, end, searched, pan, zoom):
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

    if road is selected_road:
        width = 8
        color = (255, 255, 0)
    elif road in path:
        width = 7
        color = (0, 255, 255)
    elif road in searched:
        width = 5
        color = (255, 0, 255)

    if road is start:
        width = 8
        color = (0, 255, 0)
    elif road is end:
        width = 8
        color = (255, 0, 0)

    if road.has_snapped == SnapType.DebugDeleted:
        color = (0, 255, 0)

    #print(road.is_highway)

    pygame.draw.line(screen, color, world_to_screen(road.start, pan, zoom),
                     world_to_screen(road.end, pan, zoom), width)


def draw_square(screen, point, intensity, size):
    color = (0, max(min(intensity * 200, 255), 0), 0)

    pos = (point[0] - (size / 2), point[1] - (size / 2))
    dim = (size, size)

    square = pygame.Rect(point, dim)
    pygame.draw.rect(screen, color, square)


def draw_heatmap(screen: pygame.Surface, square_size, pan, zoom):
    size = square_size * zoom

    x_max = math.ceil(screen.get_width() / square_size)
    y_max = math.ceil(screen.get_height() / square_size)

    for x in range(0, x_max):
        for y in range(0, y_max):
            world_point = (((x * square_size) - pan[0]) / zoom,
                           ((y * square_size) - pan[1]) / zoom)
            screen_point = (x * square_size,
                            y * square_size)

            intensity = population_point(world_point)
            color = (0, max(min(intensity * 100, 255), 0), 0)

            pos = (screen_point[0] - (square_size / 2), screen_point[1] - (square_size / 2))
            dim = (square_size, square_size)

            square = pygame.Rect(screen_point, dim)
            pygame.draw.rect(screen, color, square)


def zoom_change(prev, increment, center, pan): # center should be a screen coordinate, not a transformed world pos
    new_step = prev + increment

    old_level = zoom_at(prev)
    new_level = zoom_at(new_step)

    old_world = screen_to_world(center, pan, old_level)
    new_world = screen_to_world(center, pan, new_level)

    world_pan = sub_lines(new_world, old_world)

    #print("Old: " + str(old_world) + ", New: " + str(new_world))

    return new_level, world_to_screen(world_pan, (0, 0), new_level)


def zoom_at(step):
    return math.pow((step / 12) + 1, 2)
    #1 + (step * 0.5)#

def int_pos(float_tuple):
    return math.floor(float_tuple[0]), math.floor(float_tuple[1])


def path_to_road(start, end, all_roads):
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

    roads = generate()

    path = []
    path_searched = []
    path_start = None
    path_end = None

    selected_road = None
    selected_start_ids = []
    selected_end_ids = []
    selected_connections = []

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
                            point_on_road(road, 0.5)))

    while running:
        if pygame.time.get_ticks() - prev_time < 16:
            continue

        prev_time = pygame.time.get_ticks()
        screen.fill((0, 0, 0))
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 4:
                    good_var_name = zoom_change(zoom_increment, 1, pygame.mouse.get_pos(), viewport_pos)
                    zoom_level = good_var_name[0]
                    viewport_pos = add_lines(viewport_pos, good_var_name[1])
                    zoom_increment += 1
                elif event.button == 5:
                    if zoom_increment > -11:
                        good_var_name = zoom_change(zoom_increment, -1, pygame.mouse.get_pos(), viewport_pos)
                        zoom_level = good_var_name[0]
                        viewport_pos = add_lines(viewport_pos, good_var_name[1])
                        zoom_increment -= 1
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_g:
                    roads = generate()

                    road_labels = []

                    for road in roads:
                        road_labels.append((gohu_font.render(str(road.global_id), True, (255, 255, 255)),
                                            point_on_road(road, 0.5)))
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
                elif event.key == pygame.K_r:
                    global DEBUG_NEW_FEATURE
                    DEBUG_NEW_FEATURE = not DEBUG_NEW_FEATURE
                    roads = generate()
                    road_labels = []

                    for road in roads:
                        road_labels.append((gohu_font.render(str(road.global_id), True, (255, 255, 255)),
                                            point_on_road(road, 0.5),
                                            road.global_id))
                elif event.key == pygame.K_z:
                    closest = (None, 9999)
                    for road in roads:
                        dist = dist_points(screen_to_world(pygame.mouse.get_pos(), viewport_pos, zoom_level), point_on_road(road, 0.5))
                        if dist < closest[1]:
                            closest = (road, dist)
                    if closest[1] < 100:
                        path_start = closest[0]
                elif event.key == pygame.K_x:
                    closest = (None, 9999)
                    for road in roads:
                        dist = dist_points(screen_to_world(pygame.mouse.get_pos(), viewport_pos, zoom_level),
                                           point_on_road(road, 0.5))
                        if dist < closest[1]:
                            closest = (road, dist)
                    if closest[1] < 100:
                        path_end = closest[0]
                elif event.key == pygame.K_c:
                    path_data = path_astar(path_start, path_end, roads)
                    path = path_data[0]
                    path_searched = path_data[1]

        if prev_pressed[0]:
            if pygame.mouse.get_pressed()[0]:
                viewport_pos = add_lines(viewport_pos, sub_lines(pygame.mouse.get_pos(), prev_mouse))
                prev_mouse = pygame.mouse.get_pos()
            else:
                if pygame.mouse.get_pos() == drag_start:
                    closest = (None, 9999)
                    for road in roads:
                        dist = dist_points(screen_to_world(drag_start, viewport_pos, zoom_level), point_on_road(road, 0.5))
                        if dist < closest[1]:
                            closest = (road, dist)
                    if closest[1] < 100:
                        selected_road = closest[0]
                        selected_start_ids = []
                        selected_end_ids = []
                        selected_connections = []
                        set_selected(closest[0], selected_end_ids, selected_start_ids, selected_connections)
                    else:
                        selected_road = None
                        selected_start_ids = []
                        selected_end_ids = []
                        selected_connections = []
                drag_start = None
        else:
            if pygame.mouse.get_pressed()[0]:
                drag_start = pygame.mouse.get_pos()
                prev_mouse = pygame.mouse.get_pos()
        prev_pressed = pygame.mouse.get_pressed()

        if DEBUG_HEATMAP:
            draw_heatmap(screen, 50, viewport_pos, zoom_level)

        for road in roads:
            draw_road(screen, road, selected_road, selected_connections, path, path_start, path_end, path_searched, viewport_pos, zoom_level)

        if DEBUG_INFO:
            debug_labels = []

            mouse_pos = pygame.mouse.get_pos()

            debug_labels.append("Pointer [screen]: {} [world]: {} Pop at: {}".format(str(mouse_pos), screen_to_world(mouse_pos, viewport_pos, zoom_level), str(population_point(screen_to_world(pygame.mouse.get_pos(), viewport_pos, zoom_level)))))

            debug_labels.append("Pan: {}".format(viewport_pos))
            debug_labels.append("Zoom: {}x".format(str(zoom_level)))

            if selected_road is not None:
                debug_labels.append("Selected: {}".format(str(selected_road.global_id)))
                if selected_road.parent is not None:
                    debug_labels.append("    Parent: {}".format(str(selected_road.parent.global_id)))
                else:
                    debug_labels.append("    Parent: None")
                debug_labels.append("    dir: {}".format(str(selected_road.dir())))
                debug_labels.append("    links_s: {}".format(str(selected_start_ids)))
                debug_labels.append("    links_s: {}".format(str(selected_end_ids)))
                debug_labels.append("    has_snapped: {}".format(str(selected_road.has_snapped)))
            else:
                debug_labels.append("Selected: None")
                debug_labels.append("")
                debug_labels.append("")
                debug_labels.append("")
                debug_labels.append("")
                debug_labels.append("")

            debug_labels.append("Seed: {}".format(str(seed)))

            debug_labels.append("# of segments: {}".format(str(MAX_SEGS)))

            height = 10
            for label in debug_labels:
                screen.blit(gohu_font.render(label, True, (255, 255, 255)),
                            (10, height))
                height += 15

            #screen.blit(label_seed, (10, 85))

            #screen.blit(label_segs, (SCREEN_RES[0] - label_segs.get_width() - 10, 10))

        if DEBUG_ROAD_ORDER:
            for label in road_labels:
                label_pos = world_to_screen(label[1], viewport_pos, zoom_level)
                if -20 < label_pos[0] < SCREEN_RES[0] and -20 < label_pos[1] < SCREEN_RES[1]:
                    screen.blit(label[0], label_pos)

        pygame.display.flip()


def set_selected(new_selection, links_e_names, links_s_name, connected_roads):
    for road in new_selection.links_s:
        connected_roads.append(road)
        links_s_name.append(road.global_id)
    for road in new_selection.links_e:
        connected_roads.append(road)
        links_e_names.append(road.global_id)


def add_lines(l1, l2):
    return l1[0] + l2[0], l1[1] + l2[1]


def sub_lines(l1, l2):
    return l1[0] - l2[0], l1[1] - l2[1]


def dist_points(p, q):
    x_diff = q[0] - p[0]
    y_diff = q[1] - p[1]
    return math.sqrt(math.pow(x_diff, 2) + math.pow(y_diff, 2))


def cross_product(line1, line2):
    return (line1[0] * line2[1]) - (line1[1] * line2[0])


def find_intersect(p, pe, q, qe):
    r = sub_lines(pe, p)
    s = sub_lines(qe, q)

    uNumerator = cross_product(sub_lines(q, p), r)
    tNumerator = cross_product(sub_lines(q, p), s)
    denominator = cross_product(r, s)

    if denominator == 0:
        return None
    u = uNumerator / denominator
    t = tNumerator / denominator

    if 0 < u < 1:
        return (p[0] + (t * r[0]), p[1] + (t * r[1])), t, u

    return None


def point_on_road(road, factor):
    end_vector = sub_lines(road.end, road.start)
    return road.start[0] + (factor * end_vector[0]), road.start[1] + (factor * end_vector[1])


all_intersections = []


def angle_between(a1, a2):
    while a1 < 0:
        a1 += 360
    while a2 < 0:
        a2 += 360

    reg = math.fabs(a1 - a2)
    res = min(reg, math.fabs(reg - 360))

    #print("a1: {}, a2: {}, diff: {}".format(str(a1), str(a2), str(res)))

    return res


def segment_length(point1, point2):
    diff = sub_lines(point1, point2)

    return math.sqrt((diff[0] * diff[0]) + (diff[1] * diff[1]))


def population_level(seg):
    return (population_point(seg.start) + population_point(seg.end)) / 2


def population_point(point):
    x = point[0] + NOISE_SEED[0]
    y = point[1] + NOISE_SEED[1]

    value1 = (snoise2(x/10000, y/10000) + 1) / 2
    value2 = (snoise2((x/20000) + 500, (y/20000) + 500) + 1) / 2
    value3 = (snoise2((x/20000) + 1000, (y/20000) + 1000) + 1) / 2
    return math.pow(((value1 * value2) + value3), 2)


def wiggle_highway():
    return random.randint(-15, 15)


def wiggle_branch():
    return random.randint(-3, 3)


time_spent_generate = 0
time_spent_local = 0


def generate(manual_seed=None):
    global time_spent_generate
    global time_spent_local

    time_spent_generate = 0
    time_spent_local = 0

    time_spent = pygame.time.get_ticks()

    RoadSegment.seg_id = 0
    global seed
    if manual_seed is None:
        seed = time.process_time()
    else:
        seed = manual_seed

    random.seed(seed)
    global all_intersections
    all_intersections = []

    road_queue = RoadQueue()
    road_queue.push(RoadSegment((0, 0), (HIGHWAY_LENGTH, 0), True))

    segments = []

    loop_count = 0
    while not road_queue.is_empty() and len(segments) <= MAX_SEGS:
        seg = road_queue.pop()

        if local_constraints(seg, segments):
            seg.insertion_order = loop_count
            seg.connect_links()
            segments.append(seg)

            new_segments = global_goals(seg)

            for new_seg in new_segments:
                new_seg.t = seg.t + 1 + new_seg.t
                road_queue.push(new_seg)
        loop_count += 1

    time_spent_generate = pygame.time.get_ticks() - time_spent
    print("Time spent in local constraints: {}\nTime spent generate: {}".format(time_spent_local, time_spent_generate))

    return segments


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
                                                        wiggle_highway(),
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
                                                        (90 * sign) + wiggle_branch(),
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
                                                        (90 * sign) + wiggle_branch(),
                                                        False,
                                                        True,
                                                        delay)
            new_segments.append(branch)

    for seg in new_segments:
        seg.parent = previous_segment

    return new_segments


def local_constraints(inspect_seg, segments):
    priority = 0
    action = None
    last_inter_t = 1
    last_ext_t = 999

    # This part doesn't have false positives, but it does miss some lines it should catch
    time_start = pygame.time.get_ticks()

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

    for line in segments:
        inter = find_intersect(inspect_seg.start, inspect_seg.end, line.start, line.end)
        if inter is not None and 0 < inter[1] < last_inter_t and priority <= 4:
            last_inter_t = inter[1]
            priority = 4

            action = lambda _, line=line, inter=inter: snap_to_cross(inspect_seg, segments, line, inter, False)
            # ????consider finding nearby roads and delete if too similar

        if segment_length(line.end, inspect_seg.end) < SNAP_VERTEX_RADIUS and priority <= 3:
            priority = 3

            action = lambda _, line=line: snap_to_vert(inspect_seg, line, True, False)

        if inter is not None and 1 < inter[1] < last_ext_t and priority <= 2:
            if dist_points(inspect_seg.end, point_on_road(inspect_seg, inter[1])) < SNAP_EXTEND_RADIUS:
                last_ext_t = inter[1]
                point = inter[0]

                action = lambda _, line=line, inter=inter: snap_to_cross(inspect_seg, segments, line, inter, True)
                priority = 2

    global time_spent_local
    time_spent_local += pygame.time.get_ticks() - time_start

    if action is not None:
        return action(None)
    return True


def snap_to_cross(mod_road, all_segments, other_road: RoadSegment, crossing, is_extend):
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
