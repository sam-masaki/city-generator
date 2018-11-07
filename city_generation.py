from typing import Any, Tuple

import pygame
import heapq
import math
import random
from noise import snoise2


HIGHWAY_LENGTH = 400
STREET_LENGTH = 300
NOISE_SEED = 0


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
        self.got_snapped = False

    def __lt__(self, other):
        return self.t < other.t

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
        x_diff = self.end[0] - self.start[0]
        y_diff = self.end[1] - self.start[1]
        return math.sqrt(math.pow(x_diff, 2) + math.pow(y_diff, 2))

    def dir(self):
        if self.end[0] - self.start[0] == 0:
            if self.end[1] < self.start[1]:
                return 270
            else:
                return 90

        return math.degrees(math.atan((self.end[1] - self.start[1]) / (self.end[0] - self.start[0])))

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

        return True


class RoadQueue:

    def __init__(self):
        self.heap = []
        self.item_number = 0

    def push(self, segment):
        heapq.heappush(self.heap, segment)
        self.item_number += 1

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
    if road.is_highway:
        color = (255, 100, 100)
    elif road.got_snapped:
        color = (100, 255, 100)
    else:
        color = (255, 255, 255)

    #print(road.is_highway)

    pygame.draw.line(screen, color, world_to_screen(road.start, pan, zoom),
                     world_to_screen(road.end, pan, zoom), 2)


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

            draw_square(screen, screen_point, population_point(world_point), square_size)


def zoom_change(prev, increment, center, pan): # center should be a screen coordinate, not a transformed world pos
    new_step = prev + increment

    old_level = zoom_at(prev)
    new_level = zoom_at(new_step)

    old_world = screen_to_world(center, pan, old_level)
    new_world = screen_to_world(center, pan, new_level)

    world_pan = sub_lines(new_world, old_world)

    print("Old: " + str(old_world) + ", New: " + str(new_world))

    return new_level, world_to_screen(world_pan, (0, 0), new_level)


def zoom_at(step):
    return math.pow((step / 12) + 1, 2)
    #1 + (step * 0.5)#

def int_pos(float_tuple):
    return math.floor(float_tuple[0]), math.floor(float_tuple[1])


def main():
    pygame.init()

    screen = pygame.display.set_mode((1280, 720))

    running = True

    roads = generate()

    #roads.append(RoadSegment((0, 0), (0, HIGHWAY_LENGTH), False))

    zoom_level = 1
    zoom_increment = 0

    prev_mouse = (0, 0)
    viewport_pos = (0, 0)
    prev_pressed = (False, False, False)

    gohu_font = pygame.font.SysFont("GohuFont", 11)

    prev_time = pygame.time.get_ticks()

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

            #print(event)

        if prev_pressed[0]:
            if pygame.mouse.get_pressed()[0]:
                viewport_pos = add_lines(viewport_pos, sub_lines(pygame.mouse.get_pos(), prev_mouse))
                prev_mouse = pygame.mouse.get_pos()
        else:
            if pygame.mouse.get_pressed()[0]:
                prev_mouse = pygame.mouse.get_pos()
        prev_pressed = pygame.mouse.get_pressed()

        draw_heatmap(screen, 100, viewport_pos, zoom_level)

        for road in roads:
            draw_road(screen, road, viewport_pos, zoom_level)
            start = world_to_screen(road.start, viewport_pos, zoom_level)
            pygame.draw.circle(screen, (255, 100, 100), int_pos(start), 5)
            end = world_to_screen(road.end, viewport_pos, zoom_level)
            pygame.draw.circle(screen, (255, 100, 255), int_pos(end), 4)

        for inter in all_intersections:
            moved_pos = world_to_screen(inter, viewport_pos, zoom_level)
            #pygame.draw.circle(screen, (100, 100, 255), int_pos(moved_pos), 5)

        label_mouse = gohu_font.render("Pointer (screen): " + str(pygame.mouse.get_pos()) + " (world): " + str(screen_to_world(pygame.mouse.get_pos(), viewport_pos, zoom_level)), True, (255, 255, 255))
        label_pan = gohu_font.render("Pan: " + str(viewport_pos[0]) + ", " + str(viewport_pos[1]), True, (255, 255, 255))
        label_zoom = gohu_font.render("Zoom: " + str(zoom_level) + "x", True, (255, 255, 255))

        road_collider = roads[0].as_rect()
        label_noise = gohu_font.render("Points: " + str(road_collider[0]) + str(road_collider[1]) + str(road_collider[2]) + str(road_collider[3]), True, (255, 255, 255))

        screen.blit(label_mouse, (10, 10))
        screen.blit(label_pan, (10, 25))
        screen.blit(label_zoom, (10, 40))
        screen.blit(label_noise, (10, 55))
        pygame.display.flip()


def generate():
    road_queue = RoadQueue()
    road_queue.push(RoadSegment((0, 0), (HIGHWAY_LENGTH, 0), True))

    segments = []

    loop_count = 0
    while not road_queue.is_empty() and loop_count < 500:
        seg = road_queue.pop()

        if local_constraints(seg, segments):
            segments.append(seg)

            new_segments = global_goals(seg)

            for new_seg in new_segments:
                delayed_seg = new_seg.copy()
                delayed_seg.t = seg.t + 1 + delayed_seg.t
                road_queue.push(new_seg)
        loop_count += 1

    return segments


def add_lines(l1, l2):
    return l1[0] + l2[0], l1[1] + l2[1]


def sub_lines(l1, l2):
    return l1[0] - l2[0], l1[1] - l2[1]


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

    if 0 < t < 1 and 0 < u < 1:
        return p[0] + (t * r[0]), p[1] + (t * r[1])

    return None


all_intersections = []


def segment_length(point1, point2):
    diff = sub_lines(point1, point2)

    return math.sqrt((diff[0] * diff[0]) + (diff[1] * diff[1]))


def local_constraints(inspect_seg, segments):
    # for collisions with other roads, they should be treated like boxes with widths of 6 and 16 depending on highway

    # check for collisions and a minimum difference in angle
    # actually just check for intersections, fail if the angles are similar

    extras = []

    for line in segments:
        inter = find_intersect(line.start, line.end, inspect_seg.start, inspect_seg.end)
        if inter is not None:
            aa = math.fabs(line.dir() - inspect_seg.dir()) % 180
            angle_diff = min(aa, math.fabs(aa - 180))
            if angle_diff < 30:
                return False
            # if the lines are not too similar, then cut the inspecting segment down to the intersection
            all_intersections.append(inter)
            
            #print("inspect_seg: " + str(inspect_seg.start) + ", " + str(inspect_seg.end) + " line: " + str(line.start) + ", " + str(line.end) + " Intersection: " + str(inter))
            inspect_seg.end = inter
            inspect_seg.got_snapped = True
        # ????consider finding nearby roads and delete if too similar

        if segment_length(line.end, inspect_seg.end) < 50:
            inspect_seg.got_snapped = True
            # check for existing lines later, when I do links between roads


        # check if closest point to inspect_seg's end is within the snapping radius
        # changes the road's angle instead of extending

    if inspect_seg.is_highway:
        if random.random() > 0.90:
            return False
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


def global_goals(previous_segment: RoadSegment):
    new_segments = []

    if previous_segment.got_snapped:
        return new_segments

    straight_seg = previous_segment.make_extension(previous_segment.dir())
    straight_pop = population_level(straight_seg)

    if previous_segment.is_highway:
        wiggle_seg = previous_segment.make_extension(previous_segment.dir() + wiggle_highway())
        wiggle_pop = population_level(wiggle_seg)

        ext_pop = 0

        if wiggle_pop > straight_pop:
            new_segments.append(wiggle_seg)
            ext_pop = wiggle_pop
        else:
            new_segments.append(straight_seg)
            ext_pop = straight_pop

        if ext_pop > 0.1 and random.random() < 0.1:
            sign = random.randrange(-1, 2, 2)
            branch = previous_segment.make_extension(previous_segment.dir() + (90 * sign) + wiggle_branch())
            new_segments.append(branch)

    if straight_pop > 0.1:
        if not previous_segment.is_highway:
            new_segments.append(straight_seg)

        if random.random() < 0.8:
            sign = random.randrange(-1, 2, 2)
            delay = 5 if previous_segment.is_highway else 0
            branch = previous_segment.make_branch(previous_segment.dir() + (90 * sign) + wiggle_branch(), delay)
            new_segments.append(branch)

    return new_segments


if __name__ == "__main__":
    main()
