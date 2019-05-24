import math
from typing import List, Tuple, Optional

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
    drawing.init()

    screen_data = drawing.ScreenData(
        pygame.display.set_mode(config.SCREEN_RES, pygame.RESIZABLE), (0, 0))
    input_data = InputData()
    path_data = pathing.PathData()
    selection = None

    city = generation.generate()
    city_labels = []
    for road in city.roads:
        city_labels.append((str(road.global_id),
                            road.point_at(0.5)))

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
                screen_data.screen = pygame.display.set_mode(
                    event.dict["size"], pygame.RESIZABLE)
                config.SCREEN_RES = event.dict["size"]
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_g:
                    debug.SHOW_ROAD_ORDER = False
                    city_labels = []
                    selection = None
                    path_data = pathing.PathData()
                    city = generation.generate()
                    for road in city.roads:
                        city_labels.append((str(road.global_id),
                                            road.point_at(0.5)))
                # Pathing
                elif event.key == pygame.K_z:
                    path_data.start = road_near_point(input_data.pos,
                                                      screen_data, city)
                elif event.key == pygame.K_x:
                    path_data.end = road_near_point(input_data.pos,
                                                    screen_data, city)
                elif event.key == pygame.K_c:
                    pathing.astar(path_data, city.roads)
                elif event.key == pygame.K_v:
                    pathing.dijkstra(path_data, city.roads)
                # Debug Views
                handle_keys_debug(event.key)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                # Zooming
                if event.button == 4:
                    screen_data.zoom_in(input_data.pos)
                elif event.button == 5:
                    screen_data.zoom_out(input_data.pos)

        # Dragging & Selection
        if input_data.prev_pressed[0]:
            if input_data.pressed[0]:  # Continue drag
                screen_data.pan = vectors.add(
                    screen_data.pan,
                    vectors.sub(input_data.pos, input_data.drag_prev_pos))
                input_data.drag_prev_pos = input_data.pos
            else:
                if input_data.pos == input_data.drag_start:  # Select road
                    selection = debug.selection_from_road(
                        road_near_point(input_data.drag_start,
                                        screen_data, city))
                # Clear out drag information
                input_data.drag_start = None
                input_data.drag_prev_pos = (0, 0)
        else:
            if input_data.pressed[0]:  # Drag started
                input_data.drag_start = input_data.pos
                input_data.drag_prev_pos = input_data.pos

        # Drawing
        if debug.SHOW_HEATMAP:
            drawing.draw_heatmap(50, city, screen_data)
        if debug.SHOW_SECTORS:
            drawing.draw_sectors(screen_data)

        # Draw roads
        if debug.SHOW_ISOLATE_SECTOR and selection is not None:
            for sector in sectors.from_seg(selection.road):
                drawing.draw_all_roads(city.sectors[sector], screen_data)
        elif debug.SHOW_MOUSE_SECTOR:
            mouse_sec = sectors.containing_sector(
                drawing.screen_to_world(input_data.pos,
                                        screen_data.pan, screen_data.zoom))
            if mouse_sec in city.sectors:
                drawing.draw_all_roads(city.sectors[mouse_sec], screen_data)
        else:
            tl_sect = sectors.containing_sector(
                drawing.screen_to_world((0, 0),
                                        screen_data.pan, screen_data.zoom))
            br_sect = sectors.containing_sector(
                drawing.screen_to_world(config.SCREEN_RES,
                                        screen_data.pan, screen_data.zoom))
            for x in range(tl_sect[0], br_sect[0] + 1):
                for y in range(tl_sect[1], br_sect[1] + 1):
                    if (x, y) in city.sectors:
                        drawing.draw_all_roads(city.sectors[(x, y)],
                                               screen_data)

        drawing.draw_roads_selected(selection, screen_data)
        drawing.draw_roads_path(path_data, screen_data)

        if debug.SHOW_INFO:
            debug_labels = debug.labels(screen_data, input_data,
                                        path_data, selection, city)

            for x in range(len(debug_labels[0])):
                label_pos = (10, 10 + x * 15)
                drawing.draw_label_screen((debug_labels[0][x], label_pos),
                                          screen_data, 1)

            for x in range(len(debug_labels[1])):
                label_pos = (config.SCREEN_RES[0] - 10, 10 + x * 15)
                drawing.draw_label_screen((debug_labels[1][x], label_pos),
                                          screen_data, -1)

        if debug.SHOW_ROAD_ORDER:
            for label in city_labels:
                drawing.draw_label_world(label, screen_data, 1)

        pygame.display.flip()


def handle_keys_debug(key):
    if key == pygame.K_1:
        debug.SHOW_INFO = not debug.SHOW_INFO
    elif key == pygame.K_2:
        if debug.SHOW_ROAD_VIEW == debug.RoadViews.No:
            debug.SHOW_ROAD_VIEW = debug.RoadViews.Snaps
        elif debug.SHOW_ROAD_VIEW == debug.RoadViews.Branches:
            debug.SHOW_ROAD_VIEW = debug.RoadViews.No
        elif debug.SHOW_ROAD_VIEW == debug.RoadViews.Snaps:
            debug.SHOW_ROAD_VIEW = debug.RoadViews.Branches
    elif key == pygame.K_3:
        debug.SHOW_ROAD_ORDER = not debug.SHOW_ROAD_ORDER
    elif key == pygame.K_4:
        debug.SHOW_HEATMAP = not debug.SHOW_HEATMAP
    elif key == pygame.K_5:
        debug.SHOW_SECTORS = not debug.SHOW_SECTORS
    elif key == pygame.K_6:
        debug.SHOW_ISOLATE_SECTOR = not debug.SHOW_ISOLATE_SECTOR
    elif key == pygame.K_7:
        debug.SHOW_MOUSE_SECTOR = not debug.SHOW_MOUSE_SECTOR


def road_near_point(screen_pos: Tuple[float, float],
                    screen_data: 'drawing.ScreenData',
                    city: generation.City) -> Optional[roads.Segment]:
    """
    Gets the closest road to the given point within 100 units
    :param screen_pos: The screen-position to look around
    :param screen_data: The current state of the view port
    :param city: A city with sectors and roads to search
    :return: The nearest road if there is one within 100 units of the point,
    None otherwise
    """
    world_pos = drawing.screen_to_world(screen_pos, screen_data.pan,
                                        screen_data.zoom)
    closest: Tuple[roads.Segment, float] = (None, 9999)
    found_road = None
    examine_sectors = sectors.from_point(world_pos, 100)

    for sector in examine_sectors:
        if sector in city.sectors:
            for road in city.sectors[sector]:
                dist = vectors.distance(world_pos, road.point_at(0.5))
                if dist < closest[1]:
                    closest = (road, dist)
            if closest[1] < 100:
                found_road = closest[0]

    return found_road


if __name__ == "__main__":
    main()
