import math


def add(v1, v2):
    return v1[0] + v2[0], v1[1] + v2[1]


def sub(v1, v2):
    return v1[0] - v2[0], v1[1] - v2[1]


def cross_product(v1, v2):
    return (v1[0] * v2[1]) - (v1[1] * v2[0])


def distance(v1, v2):
    diff = sub(v1, v2)

    return math.sqrt(math.pow(diff[0], 2) + math.pow(diff[1], 2))
