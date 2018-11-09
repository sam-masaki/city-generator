from typing import Any, Tuple

import pygame
import heapq
import math
import random
import time
from noise import snoise2
from enum import Enum

DEBUG_INFO = True
DEBUG_SNAP_TYPE = False
DEBUG_ROAD_ORDER = False

HIGHWAY_LENGTH = 400
STREET_LENGTH = 300
NOISE_SEED = 0
SCREEN_RES = (1280, 720)

seed = time.process_time()
random.seed(seed)


class SnapType(Enum):
    No = 0
    Cross = 1
    End = 2
    Extend = 3


def road_from_dir(start, direction, length, is_highway, time_delay):
    end_x = length * math.cos(math.radians(direction))
    end_y = length * math.sin(math.radians(direction))

    seg = RoadSegment(start, (end_x, end_y), is_highway, time_delay)
    return seg


class RoadSegment:
    def __init__(self, start, end, is_highway, time_delay=0):
        self.start = start
        self.end = end
        self.is_highway = is_highway
        self.t = time_delay
        self.has_snapped = SnapType.No
        self.is_branch = False

        self.links_s = []
        self.links_e = []

        self.insertion_order = 0

    def __lt__(self, other):
        return self.t < other.t

    def __gt__(self, other):
        return self.t > other.t

    def __eq__(self, other):
        if other is None:
            return False
        if not isinstance(other, RoadSegment):
            return False
        return self.t == other.t

    def copy(self):
        return RoadSegment(self.start, self.end, self.is_highway, self.t)

    def make_extension(self, direction):
        end_x = self.end[0] + (self.length() * math.cos(math.radians(direction)))
        end_y = self.end[1] + (self.length() * math.sin(math.radians(direction)))

        ext = RoadSegment(self.end, (end_x, end_y), self.is_highway, 0)
        return ext

    def make_branch(self, direction, delay):
        end_x = self.end[0] + (STREET_LENGTH * math.cos(math.radians(direction)))
        end_y = self.end[1] + (STREET_LENGTH * math.sin(math.radians(direction)))

        ext = RoadSegment(self.end, (end_x, end_y), False, delay)
        return ext

    def length(self):
        return dist_points(self.start, self.end)

    def dir(self):
        return math.degrees(math.atan2(self.end[1] - self.start[1], self.end[0] - self.start[0]))

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

    def connect_links(self):
        for road in self.links_s:
            if self.start == road.end:
                road.links_e.append(self)
            elif self.start == road.start:
                road.links_s.append(self)
            else:
                print("This shouldn't happen but it might rn")
        for road in self.links_e:
            if self.end == road.end:
                road.links_e.append(self)
            elif self.end == road.start:
                road.links_s.append(self)
            else:
                print("This shouldn't happen but it might rn")


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


def draw_road(screen, road, pan, zoom):
    width = 2
    color = (255, 255, 255)

    if road.is_highway:
        width = 4
        color = (255, 0, 0)
    elif DEBUG_SNAP_TYPE:
        if road.has_snapped == SnapType.Cross:
            color = (255, 100, 100)
        elif road.has_snapped == SnapType.End:
            color = (100, 255, 100)
        elif road.has_snapped == SnapType.Extend:
            color = (100, 100, 255)

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
            color = (0, max(min(intensity * 200, 255), 0), 0)

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


def main():
    pygame.init()

    screen = pygame.display.set_mode(SCREEN_RES)

    running = True

    roads = generate()

    zoom_level = 1
    zoom_increment = 0

    prev_mouse = (0, 0)
    viewport_pos = (0, 0)
    prev_pressed = (False, False, False)

    gohu_font = pygame.font.SysFont("GohuFont", 11)

    prev_time = pygame.time.get_ticks()

    road_labels = []

    for road in roads:
        road_labels.append((gohu_font.render(str(road.insertion_order), True, (255, 255, 255)),
                            point_on_road(road, 0.5),
                            road.insertion_order))

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
                elif event.key == pygame.K_1:
                    global DEBUG_INFO
                    DEBUG_INFO = not DEBUG_INFO
                elif event.key == pygame.K_2:
                    global DEBUG_SNAP_TYPE
                    DEBUG_SNAP_TYPE = not DEBUG_SNAP_TYPE
                elif event.key == pygame.K_3:
                    global DEBUG_ROAD_ORDER
                    DEBUG_ROAD_ORDER = not DEBUG_ROAD_ORDER

        if prev_pressed[0]:
            if pygame.mouse.get_pressed()[0]:
                viewport_pos = add_lines(viewport_pos, sub_lines(pygame.mouse.get_pos(), prev_mouse))
                prev_mouse = pygame.mouse.get_pos()
        else:
            if pygame.mouse.get_pressed()[0]:
                prev_mouse = pygame.mouse.get_pos()
        prev_pressed = pygame.mouse.get_pressed()

        #draw_heatmap(screen, 100, viewport_pos, zoom_level)

        for road in roads:
            draw_road(screen, road, viewport_pos, zoom_level)

        if DEBUG_INFO:
            label_mouse = gohu_font.render("Pointer (screen): " + str(pygame.mouse.get_pos()) + " (world): " + str(screen_to_world(pygame.mouse.get_pos(), viewport_pos, zoom_level)), True, (255, 255, 255))
            label_pan = gohu_font.render("Pan: " + str(viewport_pos[0]) + ", " + str(viewport_pos[1]), True, (255, 255, 255))
            label_zoom = gohu_font.render("Zoom: " + str(zoom_level) + "x", True, (255, 255, 255))

            road_collider = roads[0].as_rect()
            label_noise = gohu_font.render(
                "Points: " + str(road_collider[0]) + str(road_collider[1]) + str(road_collider[2]) + str(
                    road_collider[3]), True, (255, 255, 255))
            label_seed = gohu_font.render("Seed: " + str(seed), True, (255, 255, 255))

            screen.blit(label_mouse, (10, 10))
            screen.blit(label_pan, (10, 25))
            screen.blit(label_zoom, (10, 40))
            screen.blit(label_noise, (10, 55))
            screen.blit(label_seed, (10, 70))

        if DEBUG_ROAD_ORDER:
            for label in road_labels:
                label_pos = world_to_screen(label[1], viewport_pos, zoom_level)
                if -20 < label_pos[0] < SCREEN_RES[0] and -20 < label_pos[1] < SCREEN_RES[1]:
                    screen.blit(label[0], label_pos)

        pygame.display.flip()


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
        return (p[0] + (t * r[0]), p[1] + (t * r[1])), t

    return None


def point_on_road(road, factor):
    end_vector = sub_lines(road.end, road.start)
    return road.start[0] + (factor * end_vector[0]), road.start[1] + (factor * end_vector[1])


all_intersections = []


def segment_length(point1, point2):
    diff = sub_lines(point1, point2)

    return math.sqrt((diff[0] * diff[0]) + (diff[1] * diff[1]))


def snap_to_cross(mod_road, other_road, crossing):
    aa = math.fabs(other_road.dir() - mod_road.dir()) % 180
    angle_diff = min(aa, math.fabs(aa - 180))
    if angle_diff < 30:
        return False
    # if the lines are not too similar, then cut the inspecting segment down to the intersection
    all_intersections.append(crossing)

    # print("inspect_seg: " + str(inspect_seg.start) + ", " + str(inspect_seg.end) + " line: " + str(line.start) + ", " + str(line.end) + " Intersection: " + str(inter))
    mod_road.end = crossing
    mod_road.has_snapped = SnapType.Cross
    return True


def snap_to_end(mod_road, other_road):
    mod_road.end = (other_road.end[0], other_road.end[1])

    # when I add links, check that this doesn't create a really acute intersection

    mod_road.has_snapped = SnapType.End
    return True


def snap_to_extend(mod_road, point):
    mod_road.end = (point[0], point[1])

    mod_road.has_snapped = SnapType.Extend
    return True


def population_level(seg):
    return (population_point(seg.start) + population_point(seg.end)) / 2


def population_point(point):
    x = point[0] + NOISE_SEED
    y = point[1] + NOISE_SEED

    value1 = (snoise2(x/10000, y/10000) + 1) / 2
    value2 = (snoise2((x/20000) + 500, (y/20000) + 500) + 1) / 2
    value3 = (snoise2((x/20000) + 1000, (y/20000) + 1000) + 1) / 2
    return math.pow(((value1 * value2) + value3), 2)


def wiggle_highway():
    return random.randint(-15, 15)


def wiggle_branch():
    return random.randint(-3, 3)


def generate(manual_seed=None):
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
    while not road_queue.is_empty() and len(segments) <= 500:
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

    return segments


def global_goals(previous_segment: RoadSegment):
    new_segments = []

    if previous_segment.has_snapped != SnapType.No:
        return new_segments

    straight_seg = previous_segment.make_extension(previous_segment.dir())
    straight_pop = population_level(straight_seg)

    if previous_segment.is_highway:
        wiggle_seg = previous_segment.make_extension(previous_segment.dir() + wiggle_highway())
        wiggle_pop = population_level(wiggle_seg)

        if wiggle_pop > straight_pop:
            new_segments.append(wiggle_seg)
            ext_pop = wiggle_pop
        else:
            new_segments.append(straight_seg)
            ext_pop = straight_pop

        if ext_pop > 0.1 and random.random() < 0.1:
            sign = random.randrange(-1, 2, 2)
            branch = previous_segment.make_extension(previous_segment.dir() + (90 * sign) + wiggle_branch())
            branch.is_branch = True
            new_segments.append(branch)

    if straight_pop > 0.1:
        if not previous_segment.is_highway:
            new_segments.append(straight_seg)

        if random.random() < 0.8:
            sign = random.randrange(-1, 2, 2)
            delay = 5 if previous_segment.is_highway else 0
            branch = previous_segment.make_branch(previous_segment.dir() + (90 * sign) + wiggle_branch(), delay)
            branch.is_branch = True
            new_segments.append(branch)

    for seg in new_segments:
        seg.links_s.append(previous_segment)

    return new_segments


def local_constraints(inspect_seg, segments):
    extras = []

    priority = 0
    action = None
    last_inter_t = 1
    last_ext_t = 999

    for line in segments:
        inter = find_intersect(inspect_seg.start, inspect_seg.end, line.start, line.end)
        if inter is not None and 0 < inter[1] < last_inter_t and priority <= 4:
            last_inter_t = inter[1]
            priority = 4

            action = lambda _, line=line, inter=inter[0]: snap_to_cross(inspect_seg, line, inter)
            # ????consider finding nearby roads and delete if too similar

        if segment_length(line.end, inspect_seg.end) < 50 and priority <= 3:
            priority = 3

            action = lambda _, line=line: snap_to_end(inspect_seg, line)

        if inter is not None and 1 < inter[1] < last_ext_t and priority <= 2:
            if dist_points(inspect_seg.end, point_on_road(inspect_seg, inter[1])) < 50:
                last_ext_t = inter[1]
                point = inter[0]
                action = lambda _, point=point: snap_to_extend(inspect_seg, point)
                priority = 2

    if action is not None:
        return action(None)
    return True


if __name__ == "__main__":
    main()
