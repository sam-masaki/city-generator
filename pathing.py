from heapdict import heapdict

import vectors


def astar(start, end, all_roads):
    closed = []
    open = heapdict()

    dist_start = {}
    dist_end = {}
    prev_road = {}

    for road in all_roads:
        init_start = 9999999
        init_end = 9999999

        if road is start:
            init_start = 0
            init_end = heuristic(road, end)

        dist_start[road] = init_start
        dist_end[road] = init_end
        prev_road[road] = None

    open[start] = dist_end[start]

    while len(open):
        curr_min = open.popitem()[0]
        if curr_min is end:
            break

        closed.append(curr_min)
        neighbors = curr_min.links_s.union(curr_min.links_e)

        for road in neighbors:
            if road in closed:
                continue

            new_dist_start = dist_start[curr_min] + cost(road)

            if new_dist_start < dist_start[road]:
                dist_start[road] = new_dist_start
                dist_end[road] = new_dist_start + heuristic(road, end)
                prev_road[road] = curr_min
                if road not in open:
                    open[road] = dist_end[road]

    sequence = []
    if prev_road[end] is not None or end is start:
        curr_node = end
        while curr_node is not None:
            sequence.append(curr_node)
            curr_node = prev_road[curr_node]

    return sequence, closed


def dijkstra(start, end, all_roads):
    node_queue = heapdict()

    dist_start = {}
    prev_road = {}

    searched = []

    for road in all_roads:
        dist_start[road] = 0 if road is start else 9999999
        prev_road[road] = None
        node_queue[road] = dist_start[road]

    while not len(node_queue) == 0:
        curr_min = node_queue.popitem()[0]

        if curr_min is end:
            break

        neighbors = curr_min.links_s.union(curr_min.links_e)

        for road in neighbors:
            this_dist = dist_start[curr_min] + cost(road)
            if this_dist < dist_start[road]:
                searched.append(road)

                dist_start[road] = this_dist
                prev_road[road] = curr_min
                node_queue[road] = this_dist

    sequence = []
    if prev_road[end] is not None or end is start:
        curr_node = end
        while curr_node is not None:
            sequence.append(curr_node)
            curr_node = prev_road[curr_node]

    return sequence, searched


def heuristic(road, goal):
    return vectors.distance(road.point_at(0.5), goal.point_at(0.5)) * 0.1


def cost(road):
    multiplier = 0.75 if road.is_highway else 1

    return round(road.length() * multiplier * 0.1)
