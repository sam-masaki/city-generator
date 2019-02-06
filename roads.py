import heapq
from SnapType import SnapType
import vectors
import math
import collections

Intersection = collections.namedtuple("Intersection", ["point", "main_factor", "other_factor"])

class Queue:
    def __init__(self):
        self.heap = []

    def push(self, segment):
        heapq.heappush(self.heap, segment)

    def pop(self):
        return heapq.heappop(self.heap)

    def is_empty(self):
        return self.heap == []


class Segment:
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
        self.global_id = Segment.seg_id

        Segment.seg_id += 1

    def __lt__(self, other):
        return self.t < other.t

    def __gt__(self, other):
        return self.t > other.t

    def copy(self):
        return Segment(self.start, self.end, self.is_highway, self.t)

    def make_continuation(self, length, offset, is_highway, is_branch, delay=0):
        radian_dir = math.radians(self.dir() + offset)

        end_x = self.end[0] + (length * math.cos(radian_dir))
        end_y = self.end[1] + (length * math.sin(radian_dir))

        road = Segment(self.end, (end_x, end_y), is_highway, delay)
        road.is_branch = is_branch

        return road

    def make_extension(self, deviation):
        return self.make_continuation(self.length(), deviation, self.is_highway, False)

    def length(self):
        return vectors.distance(self.start, self.end)

    def dir(self):
        angle = math.degrees(math.atan2(self.end[1] - self.start[1], self.end[0] - self.start[0]))
        if angle < 0:
            angle += 360
        return angle

    # links this road with every road that this is connected with and sets settled to true
    def connect_links(self):
        if self.parent is not None:
            for road in self.parent.links_e:
                if self.start == road.end:
                    road.links_e.add(self)
                elif self.start == road.start:
                    road.links_s.add(self)

                self.links_s.add(road)
            self.parent.links_e.add(self)
            self.links_s.add(self.parent)

        for road in self.links_e:
            if self.end == road.start:
                road.links_s.add(self)
            elif self.end == road.end:
                road.links_e.add(self)

        self.settled = True

    def point_at(self, factor):
        end_vector = vectors.sub(self.end, self.start)
        return self.start[0] + (factor * end_vector[0]), self.start[1] + (factor * end_vector[1])

    def find_intersect(self, other):
        r = vectors.sub(self.end, self.start)
        s = vectors.sub(other.end, other.start)

        t_numerator = vectors.cross_product(vectors.sub(other.start, self.start), s)
        u_numerator = vectors.cross_product(vectors.sub(other.start, self.start), r)
        denominator = vectors.cross_product(r, s)

        if denominator == 0:
            return None
        this_factor = t_numerator / denominator
        other_factor = u_numerator / denominator


        if 0 < other_factor < 1:
            return Intersection((self.start[0] + (this_factor * r[0]), self.start[1] + (this_factor * r[1])),
                                this_factor,
                                other_factor)

        return None

# Gets the angle formed by two roads
# Assumes the roads are connected and not the same
def angle_between(road1: Segment, road2: Segment):
    angle1 = road1.dir()
    angle2 = road2.dir()

    if road1.start == road2.start or road1.end == road2.end:
        diff = math.fabs(road1.dir() - road2.dir())
    else:
        diff = math.fabs(road1.dir() - road2.dir()) - 180

    while diff < 0:
        diff += 360

    return min(diff, 360 - diff)
