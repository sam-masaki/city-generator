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
from generation import generate
import drawing


def main():
    pygame.init()
    draw_data = drawing.ScreenData(pygame.display.set_mode(config.SCREEN_RES, pygame.RESIZABLE), (0, 0), 1)
    gohu_font = pygame.font.SysFont("GohuFont", 11)

    result = generate()
    all_roads = result[0]
    all_sectors = result[1]
    road_labels = []

    path_data = pathing.PathData()
    selection = None

    # Inter-frame Variables
    zoom_increment = 0
    prev_mouse = (0, 0)
    drag_start = None
    prev_pressed = (False, False, False)
    prev_time = pygame.time.get_ticks()

    running = True
    while running:
        if pygame.time.get_ticks() - prev_time < 16:
            continue

        mouse_pos = pygame.mouse.get_pos()
        mouse_world_pos = drawing.screen_to_world(mouse_pos, draw_data)
        prev_time = pygame.time.get_ticks()
        draw_data.screen.fill((0, 0, 0))

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.VIDEORESIZE:
                draw_data.screen = pygame.display.set_mode(event.dict["size"], pygame.RESIZABLE)
                config.SCREEN_RES = event.dict["size"]
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_g:
                    result = generate()
                    all_roads = result[0]
                    all_sectors = result[1]
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
                        for road in all_roads:
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
                    path_data.start = select_nearby_road(mouse_world_pos, all_roads)
                elif event.key == pygame.K_x:
                    path_data.end = select_nearby_road(mouse_world_pos, all_roads)
                elif event.key == pygame.K_c:
                    pathing.astar(path_data, all_roads)
                elif event.key == pygame.K_v:
                    pathing.dijkstra(path_data, all_roads)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                # Zooming
                if event.button == 4:
                    zoom_change(zoom_increment, 1, mouse_pos, draw_data)
                    zoom_increment += 1
                elif event.button == 5:
                    if zoom_increment > -11:
                        zoom_change(zoom_increment, -1, mouse_pos, draw_data)
                        zoom_increment -= 1

        # Dragging
        if prev_pressed[0]:
            if pygame.mouse.get_pressed()[0]:
                draw_data.pan = vectors.add(draw_data.pan, vectors.sub(mouse_pos, prev_mouse))
                prev_mouse = mouse_pos
            else:
                if mouse_pos == drag_start:
                    selected = select_nearby_road(drawing.screen_to_world(drag_start, draw_data), all_roads)
                    if selected is not None:
                        start_ids = []
                        end_ids = []
                        connections = []
                        selected_sectors = sectors.from_seg(selected)
                        for road in selected.links_s:
                            start_ids.append(road.global_id)
                            connections.append(road)
                        for road in selected.links_e:
                            end_ids.append(road.global_id)
                            connections.append(road)
                        selection = (selected, connections, start_ids, end_ids, selected_sectors)
                    else:
                        selection = None

                drag_start = None
        else:
            if pygame.mouse.get_pressed()[0]:
                drag_start = mouse_pos
                prev_mouse = mouse_pos
        prev_pressed = pygame.mouse.get_pressed()

        # Drawing
        if debug.SHOW_HEATMAP:
            drawing.draw_heatmap(50, draw_data)
        if debug.SHOW_SECTORS:
            drawing.draw_sectors(draw_data)
        if debug.SHOW_ISOLATE_SECTOR and selection is not None:
            drawing.draw_all_roads(all_sectors[sectors.containing_sector(selection[0].point_at(0.5))], draw_data)
        else:
            tl_sect = sectors.containing_sector(drawing.screen_to_world((0, 0), draw_data))
            br_sect = sectors.containing_sector(drawing.screen_to_world(config.SCREEN_RES, draw_data))
            for x in range(tl_sect[0], br_sect[0] + 1):
                for y in range(tl_sect[1], br_sect[1] + 1):
                    if (x, y) in all_sectors:
                        drawing.draw_all_roads(all_sectors[(x, y)], draw_data)
        drawing.draw_roads_selected(selection, draw_data)
        drawing.draw_roads_path(path_data, draw_data)

        if debug.SHOW_INFO:
            debug_labels_left = []
            debug_labels_right = []

            debug_labels_left.append("Pointer (screen): {}".format(str(mouse_pos)))
            debug_labels_left.append("    (world): {}".format(mouse_world_pos))
            debug_labels_left.append("    pop_at: {}".format(population.at_point(mouse_world_pos)))
            debug_labels_left.append("    sec_at: {}".format(sectors.containing_sector(mouse_world_pos)))
            debug_labels_left.append("Pan: {}".format(draw_data.pan))
            debug_labels_left.append("Zoom: {}x".format(str(draw_data.zoom)))

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
            debug_labels_left.append("Path Length: {}".format(path_data.length))

            debug_labels_right.append("Seed: {}".format(str(config.ROAD_SEED)))

            debug_labels_right.append("# of segments: {}".format(str(config.MAX_SEGS)))

            height = 10
            for label in debug_labels_left:
                draw_data.screen.blit(gohu_font.render(label, False, (255, 255, 255), (0, 0, 0)), (10, height))
                height += 15

            height = 10
            for label in debug_labels_right:
                surf = gohu_font.render(label, False, (255, 255, 255))
                draw_data.screen.blit(surf, (config.SCREEN_RES[0] - surf.get_width() - 10, height))
                height += 15
        if debug.SHOW_ROAD_ORDER:
            for label in road_labels:
                label_pos = drawing.world_to_screen(label[1], draw_data)
                if -20 < label_pos[0] < config.SCREEN_RES[0] and -20 < label_pos[1] < config.SCREEN_RES[1]:
                    draw_data.screen.blit(label[0], label_pos)

        pygame.display.flip()


def select_nearby_road(world_pos: Tuple[float, float], all_roads: List[roads.Segment]):
    closest: Tuple[roads.Segment, float] = (None, 9999)
    for road in all_roads:
        dist = vectors.distance(world_pos, road.point_at(0.5))
        if dist < closest[1]:
            closest = (road, dist)
    if closest[1] < 100:
        selected = closest[0]

        return selected

    return None


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
    return math.pow((step / 12) + 1, 2)


if __name__ == "__main__":
    main()
