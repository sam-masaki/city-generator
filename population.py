from noise import snoise2
from typing import Tuple
import math
import roads


class Heatmap:
    def __init__(self, seed):
        self.seed = seed

    def at_line(self, seg: roads.Segment) -> float:
        return (self.at_point(seg.start) + self.at_point(seg.end)) / 2

    def at_point(self, point: Tuple[float, float]) -> float:
        x = point[0] + self.seed[0]
        y = point[1] + self.seed[1]

        value1 = (snoise2(x/10000, y/10000) + 1) / 2
        value2 = (snoise2((x/20000) + 500, (y/20000) + 500) + 1) / 2
        value3 = (snoise2((x/20000) + 1000, (y/20000) + 1000) + 1) / 2

        return math.pow(((value1 * value2) + value3), 2)
