from typing import Any, Tuple

import pygame
import heapq
import math
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
    def __init__(self, start, end, is_highway, time_delay=-1):
        self.start = start
        self.end = end
        self.is_highway = is_highway
        self.t = time_delay


class RoadQueue:

    def __init__(self):
        self.heap = []
        self.item_number = 0

    def push(self, segment):
        heapq.heappush(self.heap, (segment.t + self.item_number, segment))
        self.item_number += 1

    def pop(self):
        return heapq.heappop(self.heap)

    def is_empty(self):
        return self.heap == []


def viewport_transform(original_pos, pan, zoom):
    result = ((original_pos[0] * zoom) + pan[0],
              (original_pos[1] * zoom) + pan[1])
    return result


def main():
    pygame.init()

    screen = pygame.display.set_mode((1280, 720))

    running = True

    roads = [] #generate()

    roads.append(RoadSegment((0, 0), (STREET_LENGTH, 15), True))
    roads.append(RoadSegment((STREET_LENGTH, 15), (-15, HIGHWAY_LENGTH), True))

    zoom_level = 2
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
                    zoom_level += 0.1
                elif event.button == 5:
                    zoom_level -= 0.1

            #print(event)

        if prev_pressed[0]:
            if pygame.mouse.get_pressed()[0]:
                viewport_pos = (viewport_pos[0] + pygame.mouse.get_pos()[0] - prev_mouse[0],
                                viewport_pos[1] + pygame.mouse.get_pos()[1] - prev_mouse[1])
                prev_mouse = pygame.mouse.get_pos()
        else:
            if pygame.mouse.get_pressed()[0]:
                prev_mouse = pygame.mouse.get_pos()
        prev_pressed = pygame.mouse.get_pressed()

        for road in roads:
            pygame.draw.line(screen, (255, 255, 255), viewport_transform(road.start, viewport_pos, zoom_level), viewport_transform(road.end, viewport_pos, zoom_level), 2)

        label_pan = gohu_font.render("Pan: " + str(viewport_pos[0]) + ", " + str(viewport_pos[1]), True, (255, 255, 255))
        label_zoom = gohu_font.render("Zoom: " + str(zoom_level) + "x", True, (255, 255, 255))
        label_noise = gohu_font.render("Noise at 1, 1: " + str(population_level(roads[1])), True, (255, 255, 255))

        screen.blit(label_pan, (10, 10))
        screen.blit(label_zoom, (10, 25))
        screen.blit(label_noise, (10, 40))
        pygame.display.flip()


def generate():
    road_queue = RoadQueue()
    road_queue.push(RoadSegment((0, 0), (0, HIGHWAY_LENGTH), True))

    segments = []

    loop_count = 0
    while not road_queue.is_empty() and loop_count < 5:
        seg = road_queue.pop()

        if local_constraints(seg, segments):
            segments.append(seg)

            new_segments = global_goals(seg)

            for new_seg in new_segments:
                road_queue.push(new_seg)
        loop_count += 1

    return segments


def local_constraints(inspect_seg, segments) -> object:
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


def global_goals(previous_segment):
    new_segments = []

    random_angle_mod = 0

    straight_seg = road_from_dir(previous_segment.end, previous_segment.dir, previous_segment.length, previous_segment.is_highway, 0)
    straight_pop = population_level(straight_seg)

    if previous_segment.is_highway:
        wiggle_seg = road_from_dir(previous_segment.end, previous_segment.dir + random_angle_mod,
                                   previous_segment.length, previous_segment.is_highway, 0)
        wiggle_pop = population_level(wiggle_seg)
    else:
        a = 0

    return new_segments


if __name__ == "__main__":
    main()
