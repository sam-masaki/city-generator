import math
from typing import List, Tuple

import pygame

import pathing
import population
import roads
import sectors
import vectors
from SnapType import SnapType
from config import *
from debug import *
from generation import generate


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
                    path_data = pathing.dijkstra(path_start, path_end, roads)
                    path = path_data[0]
                    path_searched = path_data[1]
            elif event.type == pygame.MOUSEBUTTONDOWN:

                # Zooming
                if event.button == 4:
                    good_var_name = zoom_change(zoom_increment, 1, pygame.mouse.get_pos(), viewport_pos)
                    zoom_level = good_var_name[0]
                    viewport_pos = vectors.add(viewport_pos, good_var_name[1])
                    zoom_increment += 1
                elif event.button == 5:
                    if zoom_increment > -11:
                        good_var_name = zoom_change(zoom_increment, -1, pygame.mouse.get_pos(), viewport_pos)
                        zoom_level = good_var_name[0]
                        viewport_pos = vectors.add(viewport_pos, good_var_name[1])
                        zoom_increment -= 1

        if prev_pressed[0]:
            if pygame.mouse.get_pressed()[0]:
                viewport_pos = vectors.add(viewport_pos, vectors.sub(pygame.mouse.get_pos(), prev_mouse))
                prev_mouse = pygame.mouse.get_pos()
            else:
                if pygame.mouse.get_pos() == drag_start:
                    selected = select_nearby_road(screen_to_world(drag_start, viewport_pos, zoom_level), roads)
                    if selected is not None:
                        start_ids = []
                        end_ids = []
                        connections = []
                        all_sectors = sectors.from_seg(selected)
                        for road in selected.links_s:
                            start_ids.append(road.global_id)
                            connections.append(road)
                        for road in selected.links_e:
                            end_ids.append(road.global_id)
                            connections.append(road)
                        selection = (selected, connections, start_ids, end_ids, all_sectors)
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
            draw_all_roads(sects[sectors.containing_sector(selection[0].point_at(0.5))], screen, viewport_pos, zoom_level)
        else:
            tl_sect = sectors.containing_sector(screen_to_world((0, 0), viewport_pos, zoom_level))
            br_sect = sectors.containing_sector(screen_to_world(SCREEN_RES, viewport_pos, zoom_level))
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
            debug_labels_left.append("    pop_at: {}".format(population.at_point(screen_to_world(pygame.mouse.get_pos(), viewport_pos, zoom_level))))
            debug_labels_left.append("    sec_at: {}".format(sectors.containing_sector(screen_to_world(pygame.mouse.get_pos(), viewport_pos, zoom_level))))
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

            debug_labels_right.append("Seed: {}".format(str(ROAD_SEED)))

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


def select_nearby_road(world_pos: Tuple[float, float], roads: List[roads.Segment]) -> roads.Segment:
    closest: Tuple[roads.Segment, float] = (None, 9999)
    for road in roads:
        dist = vectors.distance(world_pos, road.point_at(0.5))
        if dist < closest[1]:
            closest = (road, dist)
    if closest[1] < 100:
        selected = closest[0]

        return selected

    return None


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


def draw_heatmap(screen: pygame.Surface, square_size, pan, zoom):
    x_max = vectors.math.ceil(screen.get_width() / square_size) + 1
    y_max = vectors.math.ceil(screen.get_height() / square_size) + 1

    for x in range(0, x_max):
        for y in range(0, y_max):
            screen_point = (x * square_size,
                            y * square_size)
            world_point = screen_to_world(screen_point, pan, zoom)

            intensity = population.at_point(world_point)
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

    world_pan = vectors.sub(new_world, old_world)

    return new_level, world_to_screen(world_pan, (0, 0), new_level)


def zoom_at(step):
    return math.pow((step / 12) + 1, 2)


if __name__ == "__main__":
    main()
