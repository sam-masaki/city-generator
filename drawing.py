import config
import debug
import pathing
from SnapType import SnapType
import pygame
import math
import population
import vectors


class ScreenData:
    def __init__(self, screen, pan):
        self.screen = screen
        self.pan = pan
        self._zoom_increment = 1
        self.zoom = self._zoom_at(1)

    @staticmethod
    def _zoom_at(step):
        return math.pow((step / config.ZOOM_GRANULARITY) + 1, 2)

    def zoom_in(self, center):
        self._zoom_change(1, center)

    def zoom_out(self, center):
        if self._zoom_increment > (-config.ZOOM_GRANULARITY) + 3:
            self._zoom_change(-1, center)

    def _zoom_change(self, step, center):
        new_level = self._zoom_at(self._zoom_increment + step)

        old_world = screen_to_world(center, self.pan, self.zoom)
        new_world = screen_to_world(center, self.pan, new_level)

        world_pan = vectors.sub(new_world, old_world)

        self.zoom = new_level
        self.pan = vectors.add(self.pan, world_to_screen(world_pan, (0, 0), new_level))

        self._zoom_increment += step
        return


def world_to_screen(world_pos, pan, zoom):
    result = ((world_pos[0] * zoom) + pan[0],
              (world_pos[1] * zoom) + pan[1])
    return result


def screen_to_world(screen_pos, pan, zoom):
    result = (((screen_pos[0] - pan[0]) / zoom),
              ((screen_pos[1] - pan[1]) / zoom))
    return result


def draw_all_roads(all_roads, data: ScreenData):
    for road in all_roads:
        width = config.ROAD_WIDTH
        color = (255, 255, 255)

        if road.is_highway:
            width = config.ROAD_WIDTH_HIGHWAY
            color = (255, 0, 0)
        elif debug.SHOW_ROAD_VIEW == debug.RoadViews.Snaps:
            if road.has_snapped == SnapType.Cross:
                color = (255, 100, 100)
            elif road.has_snapped == SnapType.End:
                color = (100, 255, 100)
            elif road.has_snapped == SnapType.Extend:
                color = (100, 100, 255)
            elif road.has_snapped == SnapType.CrossTooClose:
                color = (100, 255, 255)
        elif debug.SHOW_ROAD_VIEW == debug.RoadViews.Branches:
            if road.is_branch:
                color = (100, 255, 100)
        if road.has_snapped == SnapType.DebugDeleted:
            color = (0, 255, 0)

        draw_road(road, color, width, data)


def draw_roads_selected(selection, data: ScreenData):
    if selection is not None:
        draw_road(selection[0], (255, 255, 0), config.ROAD_WIDTH_SELECTION, data)

        for road in selection[1]:
            draw_road(road, (0, 255, 0), config.ROAD_WIDTH_SELECTION, data)


def draw_roads_path(path_data: pathing.PathData, data: ScreenData):
    if len(path_data.searched) != 0:
        width = config.ROAD_WIDTH_PATH
        color = (255, 0, 255)

        for road in path_data.searched:
            draw_road(road, color, width, data)

    if len(path_data.path) != 0:
        width = config.ROAD_WIDTH_PATH
        color = (0, 255, 255)
        for road in path_data.path:
            draw_road(road, color, width, data)

    width = config.ROAD_WIDTH_PATH
    if path_data.start is not None:
        draw_road(path_data.start, (0, 255, 0), width, data)
    if path_data.end is not None:
        draw_road(path_data.end, (255, 0, 0), width, data)


def draw_road(road, color, width, data):
    pygame.draw.line(data.screen, color, world_to_screen(road.start, data.pan, data.zoom), world_to_screen(road.end, data.pan, data.zoom), width)


def draw_heatmap(square_size, data):
    x_max = math.ceil(config.SCREEN_RES[0] / square_size) + 1
    y_max = math.ceil(config.SCREEN_RES[1] / square_size) + 1

    for x in range(0, x_max):
        for y in range(0, y_max):
            screen_point = (x * square_size,
                            y * square_size)
            world_point = screen_to_world(screen_point, data.pan, data.zoom)

            intensity = population.at_point(world_point)
            color = (0, max(min(intensity * 100, 255), 0), 0)

            pos = (screen_point[0] - (square_size / 2), screen_point[1] - (square_size / 2))
            dim = (square_size, square_size)

            pygame.draw.rect(data.screen, color, pygame.Rect(pos, dim))


def draw_sectors(data):
    x_min = round(screen_to_world((0, 0), data.pan, data.zoom)[0] // config.SECTOR_SIZE) + 1
    x_max = round(screen_to_world((config.SCREEN_RES[0], 0), data.pan, data.zoom)[0] // config.SECTOR_SIZE) + 1

    x_range = range(x_min, x_max)
    for x in x_range:
        pos_x = world_to_screen((config.SECTOR_SIZE * x, 0), data.pan, data.zoom)[0]

        pygame.draw.line(data.screen, (100, 200, 100),
                         (pos_x + (config.MIN_DIST_EDGE_CONTAINED * data.zoom), 0),
                         (pos_x + (config.MIN_DIST_EDGE_CONTAINED * data.zoom), config.SCREEN_RES[1]))
        pygame.draw.line(data.screen, (100, 200, 100),
                         (pos_x - (config.MIN_DIST_EDGE_CONTAINED * data.zoom), 0),
                         (pos_x - (config.MIN_DIST_EDGE_CONTAINED * data.zoom), config.SCREEN_RES[1]))

        pygame.draw.line(data.screen, (200, 200, 200), (pos_x, 0), (pos_x, config.SCREEN_RES[1]))

    y_min = round(screen_to_world((0, 0), data.pan, data.zoom)[1] // config.SECTOR_SIZE) + 1
    y_max = round(screen_to_world((0, config.SCREEN_RES[1]), data.pan, data.zoom)[1] // config.SECTOR_SIZE) + 1

    y_range = range(y_min, y_max)
    for y in y_range:
        pos_y = world_to_screen((0, config.SECTOR_SIZE * y), data.pan, data.zoom)[1]

        pygame.draw.line(data.screen, (100, 200, 100),
                         (0, pos_y + (config.MIN_DIST_EDGE_CONTAINED * data.zoom)),
                         (config.SCREEN_RES[0], pos_y + (config.MIN_DIST_EDGE_CONTAINED * data.zoom)))

        pygame.draw.line(data.screen, (100, 200, 100),
                         (0, pos_y - (config.MIN_DIST_EDGE_CONTAINED * data.zoom)),
                         (config.SCREEN_RES[0], pos_y - (config.MIN_DIST_EDGE_CONTAINED * data.zoom)))

        pygame.draw.line(data.screen, (200, 200, 200), (0, pos_y), (config.SCREEN_RES[0], pos_y))
