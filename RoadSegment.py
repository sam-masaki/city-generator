from SnapType import SnapType
import math
from vector_operations import *


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
        return dist_vectors(self.start, self.end)

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
        return dist_vectors(self.point_at(0.5), goal.point_at(0.5)) * 0.1

    def point_at(self, factor):
        end_vector = sub_vectors(self.end, self.start)
        return self.start[0] + (factor * end_vector[0]), self.start[1] + (factor * end_vector[1])
