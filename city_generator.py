import math
from typing import List, Tuple

import pygame

import pathing
import population
import roads
import sectors
import vectors
import config
import debug
import generation
import drawing
import collections
from Stopwatch import Stopwatch


class InputData:
    def __init__(self):
        self.zoom_incr = 0
        self.pos = (0, 0)
        self._pressed = (False, False, False)
        self._prev_pressed = (False, False, False)
        self.drag_start = None
        self.drag_prev_pos = (0, 0)

    @property
    def pressed(self):
        return self._pressed

    @pressed.setter
    def pressed(self, value):
        self._prev_pressed = self._pressed
        self._pressed = value

    @property
    def prev_pressed(self):
        return self._prev_pressed


def main():
    pygame.init()

    screen_data = drawing.ScreenData(pygame.display.set_mode(config.SCREEN_RES, pygame.RESIZABLE), (0, 0), 1)
    input_data = InputData()
    path_data = pathing.PathData()
    selection = None

    gohu_font = pygame.font.SysFont("gohufont, terminusttf, couriernew", 14)

    city = generation.generate()
    road_labels = []

    # Inter-frame Variables

    prev_time = pygame.time.get_ticks()

    running = True
    while running:
        if pygame.time.get_ticks() - prev_time < 16:
            continue

        input_data.pos = pygame.mouse.get_pos()
        input_data.pressed = pygame.mouse.get_pressed()

        prev_time = pygame.time.get_ticks()
        screen_data.screen.fill((0, 0, 0))

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.VIDEORESIZE:
                screen_data.screen = pygame.display.set_mode(event.dict["size"], pygame.RESIZABLE)
                config.SCREEN_RES = event.dict["size"]
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_g:
                    city = generation.generate()
                # Debug Views
                elif event.key == pygame.K_1:
                    debug.SHOW_INFO = not debug.SHOW_INFO
                elif event.key == pygame.K_2:
                    if debug.SHOW_ROAD_VIEW == debug.RoadViews.No:
                        debug.SHOW_ROAD_VIEW = debug.RoadViews.Snaps
                    elif debug.SHOW_ROAD_VIEW == debug.RoadViews.Branches:
                        debug.SHOW_ROAD_VIEW = debug.RoadViews.No
                    elif debug.SHOW_ROAD_VIEW == debug.RoadViews.Snaps:
                        debug.SHOW_ROAD_VIEW = debug.RoadViews.Branches
                elif event.key == pygame.K_3:
                    debug.SHOW_ROAD_ORDER = not debug.SHOW_ROAD_ORDER
                    if debug.SHOW_ROAD_ORDER:
                        road_labels = []
                        for road in city.roads:
                            road_labels.append((gohu_font.render(str(road.global_id), True, (255, 255, 255)),
                                                road.point_at(0.5)))
                elif event.key == pygame.K_4:
                    debug.SHOW_HEATMAP = not debug.SHOW_HEATMAP
                elif event.key == pygame.K_5:
                    debug.SHOW_SECTORS = not debug.SHOW_SECTORS
                elif event.key == pygame.K_6:
                    debug.SHOW_ISOLATE_SECTOR = not debug.SHOW_ISOLATE_SECTOR

                # Pathing
                elif event.key == pygame.K_z:
                    path_data.start = road_near_point(drawing.screen_to_world(input_data.pos, screen_data), city)
                elif event.key == pygame.K_x:
                    path_data.end = road_near_point(drawing.screen_to_world(input_data.pos, screen_data), city)
                elif event.key == pygame.K_c:
                    pathing.astar(path_data, city.roads)
                elif event.key == pygame.K_v:
                    pathing.dijkstra(path_data, city.roads)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                # Zooming
                if event.button == 4:
                    zoom_change(input_data.zoom_incr, 1, input_data.pos, screen_data)
                    input_data.zoom_incr += 1
                elif event.button == 5:
                    if input_data.zoom_incr > (-config.ZOOM_GRANULARITY) + 1:
                        zoom_change(input_data.zoom_incr, -1, input_data.pos, screen_data)
                        input_data.zoom_incr -= 1

        # Dragging
        if input_data.prev_pressed[0]:
            if input_data.pressed[0]:
                screen_data.pan = vectors.add(screen_data.pan, vectors.sub(input_data.pos, input_data.drag_prev_pos))
                input_data.drag_prev_pos = input_data.pos
            else:
                if input_data.pos == input_data.drag_start:
                    selection = debug.selection_from_road(road_near_point(drawing.screen_to_world(input_data.drag_start, screen_data), city))

                input_data.drag_start = None
                input_data.drag_prev_pos = (0, 0)
        else:
            if input_data.pressed[0]:
                input_data.drag_start = input_data.pos
                input_data.drag_prev_pos = input_data.pos

        # Drawing
        if debug.SHOW_HEATMAP:
            drawing.draw_heatmap(50, screen_data)
        if debug.SHOW_SECTORS:
            drawing.draw_sectors(screen_data)
        if debug.SHOW_ISOLATE_SECTOR and selection is not None:
            drawing.draw_all_roads(city.sectors[sectors.containing_sector(selection.road.point_at(0.5))], screen_data)
        else:
            tl_sect = sectors.containing_sector(drawing.screen_to_world((0, 0), screen_data))
            br_sect = sectors.containing_sector(drawing.screen_to_world(config.SCREEN_RES, screen_data))
            for x in range(tl_sect[0], br_sect[0] + 1):
                for y in range(tl_sect[1], br_sect[1] + 1):
                    if (x, y) in city.sectors:
                        drawing.draw_all_roads(city.sectors[(x, y)], screen_data)

        drawing.draw_roads_selected(selection, screen_data)
        drawing.draw_roads_path(path_data, screen_data)

        if debug.SHOW_INFO:
            debug_labels = debug.labels(screen_data, input_data, path_data, selection)

            for x in range(len(debug_labels[0])):
                screen_data.screen.blit(
                    gohu_font.render(debug_labels[0][x], False, (255, 255, 255), (0, 0, 0)), (10, 10 + x * 15))

            for x in range(len(debug_labels[1])):
                label = gohu_font.render(debug_labels[1][x], False, (255, 255, 255), (0, 0, 0))
                screen_data.screen.blit(
                    label, (config.SCREEN_RES[0] - label.get_width() - 10, 10 + x * 15))
                
        if debug.SHOW_ROAD_ORDER:
            for label in road_labels:
                label_pos = drawing.world_to_screen(label[1], screen_data)
                if -20 < label_pos[0] < config.SCREEN_RES[0] and -20 < label_pos[1] < config.SCREEN_RES[1]:
                    screen_data.screen.blit(label[0], label_pos)

        pygame.display.flip()


def road_near_point(world_pos: Tuple[float, float], city: generation.City):
    closest: Tuple[roads.Segment, float] = (None, 9999)
    found_road = None
    examine_sectors = sectors.from_point(world_pos, 100)

    for sector in examine_sectors:
        for road in city.sectors[sector]:
            dist = vectors.distance(world_pos, road.point_at(0.5))
            if dist < closest[1]:
                closest = (road, dist)
        if closest[1] < 100:
            found_road = closest[0]

    return found_road


def zoom_change(prev, increment, center, data):
    new_step = prev + increment

    old_level = zoom_at(prev)
    new_level = zoom_at(new_step)

    old_world = drawing.screen_to_world(center, drawing.ScreenData(None, data.pan, old_level))
    new_world = drawing.screen_to_world(center, drawing.ScreenData(None, data.pan, new_level))

    world_pan = vectors.sub(new_world, old_world)

    data.zoom = new_level
    data.pan = vectors.add(data.pan, drawing.world_to_screen(world_pan, drawing.ScreenData(None, (0, 0), new_level)))
    return


def zoom_at(step):
    return math.pow((step / config.ZOOM_GRANULARITY) + 1, 2)


if __name__ == "__main__":
    main()
