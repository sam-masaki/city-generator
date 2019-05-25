import heapq
from SnapType import SnapType
import vectors
import math
import collections
from typing import Tuple, Optional, List

Intersection = collections.namedtuple("Intersection", ["point", "main_factor", "other_factor"])


class Queue:
    def __init__(self):
        self.heap: List[Segment] = []

    def push(self, segment: 'Segment'):
        heapq.heappush(self.heap, segment)

    def pop(self) -> 'Segment':
        return heapq.heappop(self.heap)

    def is_empty(self):
        return self.heap == []


class Segment:
    seg_id = 0

    def __init__(self, start: Tuple[float, float], end: Tuple[float, float], is_highway: bool, time_delay: int = 0):
        self.start = start
        self.end = end
        self.is_highway = is_highway
        self.t = time_delay
        self.has_snapped = SnapType.No
        self.is_branch = False

        self.parent = None
        self.links_s = set()
        self.links_e = set()
        self.connected = False

        self.global_id = Segment.seg_id

        Segment.seg_id += 1

    def __lt__(self, other: 'Segment'):
        return self.t < other.t

    def __gt__(self, other: 'Segment'):
        return self.t > other.t

    def copy(self):
        return Segment(self.start, self.end, self.is_highway, self.t)

    def make_continuation(self, length: float, deviation: float, is_highway: bool, is_branch: bool, delay: int = 0)\
            -> 'Segment':
        """
        Builds a new segment that starts at the end of this segment
        
        :param length: Length of the new segment
        :param deviation: Angle in deg of deviation from this segment
        :param is_highway: Sets is_highway of new segment
        :param is_branch: Sets is_branch of new segment
        :param delay: Time delay of new segment
        :return: The new segment
        """
        radian_dir = math.radians(self.dir() + deviation)

        end_x = self.end[0] + (length * math.cos(radian_dir))
        end_y = self.end[1] + (length * math.sin(radian_dir))

        road = Segment(self.end, (end_x, end_y), is_highway, delay)
        road.is_branch = is_branch

        return road

    def make_extension(self, deviation: float) -> 'Segment':
        """
        Builds a new segment that starts at the end of this segment and
        has the same length and is_highway value
        :param deviation: Angle in deg of deviation from this segment
        :return: The new segment
        """
        return self.make_continuation(self.length(), deviation, self.is_highway, False)

    def length(self) -> float:
        return vectors.distance(self.start, self.end)

    def dir(self) -> float:
        """ Returns this segment's angle in degrees with 3 o'clock being zero and increasing clockwise """
        angle = math.degrees(math.atan2(self.end[1] - self.start[1], self.end[0] - self.start[0]))
        if angle < 0:
            angle += 360

        return angle

    def connect_links(self):
        """
        Adds this road to the links of each road this is connected to
        """

        # Unconnected roads have no connections going to them,
        # and a set of one-way links to roads at its end

        # Link to parent and siblings
        if self.parent is not None:
            for road in self.parent.links_e:
                if self.start == road.end:
                    road.links_e.add(self)
                elif self.start == road.start:
                    road.links_s.add(self)

                self.links_s.add(road)
            self.parent.links_e.add(self)
            self.links_s.add(self.parent)

        # Link to roads at self.end
        for road in self.links_e:
            if self.end == road.start:
                road.links_s.add(self)
            elif self.end == road.end:
                road.links_e.add(self)

        self.connected = True

    def point_at(self, factor: float) -> Tuple[float, float]:
        """
        Gets the point along the road (length * factor) away from the start
        :param factor: Fraction of the way down the road, between 0 and 1
        :return: The point along the road
        """
        end_vector = vectors.sub(self.end, self.start)

        return self.start[0] + (factor * end_vector[0]), self.start[1] + (factor * end_vector[1])

    def find_intersect(self, other: 'Segment') -> Optional[Intersection]:
        """
        Gets the Intersection between this and another road if they intersect or if this road can be extended
        to intersect with it
        :param other: Another Segment to check for an intersection with
        :return: An Intersection tuple with the point and the factors for each road
        """
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


def angle_between(road1: Segment, road2: Segment) -> float:
    """
    Gets the smaller angle in deg formed by two connected roads
    """
    diff = math.fabs(road1.dir() - road2.dir())

    if road1.start != road2.start and road1.end != road2.end:
        diff -= 180
        if diff < 0:
            diff += 360

    return min(diff, 360 - diff)
