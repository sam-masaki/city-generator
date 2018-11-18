import math


def add_vectors(v1, v2):
    return v1[0] + v2[0], v1[1] + v2[1]


def sub_vectors(v1, v2):
    return v1[0] - v2[0], v1[1] - v2[1]


def find_intersect(p, pe, q, qe):
    r = sub_vectors(pe, p)
    s = sub_vectors(qe, q)

    u_numerator = cross_product(sub_vectors(q, p), r)
    t_numerator = cross_product(sub_vectors(q, p), s)
    denominator = cross_product(r, s)

    if denominator == 0:
        return None
    u = u_numerator / denominator
    t = t_numerator / denominator

    if 0 < u < 1:
        return (p[0] + (t * r[0]), p[1] + (t * r[1])), t, u

    return None


def cross_product(v1, v2):
    return (v1[0] * v2[1]) - (v1[1] * v2[0])


def dist_vectors(v1, v2):
    diff = sub_vectors(v1, v2)

    return math.sqrt(math.pow(diff[0], 2) + math.pow(diff[1], 2))
