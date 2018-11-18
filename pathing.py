from heapdict import heapdict

import vectors


class PathData:
    def __init__(self):
        self.path = []
        self.searched = []
        self.start = None
        self.end = None
        self.length = 0


def astar(data: PathData, all_roads):
    data.searched = []
    open = heapdict()

    dist_start = {}
    dist_end = {}
    prev_road = {}

    for road in all_roads:
        init_start = 9999999
        init_end = 9999999

        if road is data.start:
            init_start = 0
            init_end = heuristic(road, data.end)

        dist_start[road] = init_start
        dist_end[road] = init_end
        prev_road[road] = None

    open[data.start] = dist_end[data.start]

    while len(open):
        curr_min = open.popitem()[0]
        if curr_min is data.end:
            break

        data.searched.append(curr_min)
        neighbors = curr_min.links_s.union(curr_min.links_e)

        for road in neighbors:
            if road in data.searched:
                continue

            new_dist_start = dist_start[curr_min] + cost(road)

            if new_dist_start < dist_start[road]:
                dist_start[road] = new_dist_start
                dist_end[road] = new_dist_start + heuristic(road, data.end)
                prev_road[road] = curr_min
                if road not in open:
                    open[road] = dist_end[road]

    data.path = []
    data.length = retrace_path(prev_road, data)
    return


def dijkstra(data: PathData, all_roads):
    node_queue = heapdict()

    dist_start = {}
    prev_road = {}

    data.searched = []

    for road in all_roads:
        dist_start[road] = 0 if road is data.start else 9999999
        prev_road[road] = None
        node_queue[road] = dist_start[road]

    while not len(node_queue) == 0:
        curr_min = node_queue.popitem()[0]

        if curr_min is data.end:
            break

        neighbors = curr_min.links_s.union(curr_min.links_e)

        for road in neighbors:
            this_dist = dist_start[curr_min] + cost(road)
            if this_dist < dist_start[road]:
                data.searched.append(road)

                dist_start[road] = this_dist
                prev_road[road] = curr_min
                node_queue[road] = this_dist

    data.path = []
    data.length = retrace_path(prev_road, data)
    return


def retrace_path(previous_node, data):
    length = 0
    if previous_node[data.end] is not None or data.end is data.start:
        curr_node = data.end
        while curr_node is not None:
            data.path.append(curr_node)
            length += cost(curr_node)
            curr_node = previous_node[curr_node]
    return length


def heuristic(road, goal):
    return vectors.distance(road.point_at(0.5), goal.point_at(0.5)) * 0.1


def cost(road):
    multiplier = 0.75 if road.is_highway else 1

    return round(road.length() * multiplier * 0.1)
