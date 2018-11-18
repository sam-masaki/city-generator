from config import NOISE_SEED
from noise import snoise2
import math


def at_line(seg):
    return (at_point(seg.start) + at_point(seg.end)) / 2


def at_point(point):
    x = point[0] + NOISE_SEED[0]
    y = point[1] + NOISE_SEED[1]

    value1 = (snoise2(x/10000, y/10000) + 1) / 2
    value2 = (snoise2((x/20000) + 500, (y/20000) + 500) + 1) / 2
    value3 = (snoise2((x/20000) + 1000, (y/20000) + 1000) + 1) / 2
    return math.pow(((value1 * value2) + value3), 2)
