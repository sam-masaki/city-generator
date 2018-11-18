from heapdict import heapdict


def astar(start, end, all_roads):
    closed = []
    open = heapdict()

    for road in all_roads:
        road.pathing_dist_start = 0 if road is start else 9999999
        road.pathing_dist_end = road.pathing_heuristic(end) if road is start else 9999999
        road.pathing_prev = None
    open[start] = start.pathing_dist_end

    while len(open):
        curr_min = open.popitem()[0]
        if curr_min is end:
            break

        closed.append(curr_min)
        neighbors = curr_min.links_s.union(curr_min.links_e)

        for road in neighbors:
            if road in closed:
                continue

            new_dist_start = curr_min.pathing_dist_start + road.pathing_cost()

            if new_dist_start < road.pathing_dist_start:
                road.pathing_dist_start = new_dist_start
                road.pathing_dist_end = road.pathing_dist_start + road.pathing_heuristic(end)
                road.pathing_prev = curr_min
                if road not in open:
                    open[road] = road.pathing_dist_end

    sequence = []
    if end.pathing_prev is not None or end is start:
        curr_node = end
        while curr_node is not None:
            sequence.append(curr_node)
            curr_node = curr_node.pathing_prev

    return sequence, closed


def dijkstra(start, end, all_roads):
    node_queue = heapdict()
    for road in all_roads:
        road.pathing_dist_start = 0 if road is start else 9999999
        road.pathing_prev = None
        node_queue[road] = road.pathing_dist_start

    while not len(node_queue) == 0:
        curr_min = node_queue.popitem()[0]

        if curr_min is end:
            break

        neighbors = curr_min.links_s.union(curr_min.links_e)

        for road in neighbors:
            this_dist = curr_min.pathing_dist_start + road.pathing_cost()
            if this_dist < road.pathing_dist_start:
                road.pathing_dist_start = this_dist
                road.pathing_prev = curr_min
                node_queue[road] = this_dist

    sequence = []
    if end.pathing_prev is not None or end is start:
        curr_node = end
        while curr_node is not None:
            sequence.append(curr_node)
            curr_node = curr_node.pathing_prev

    return sequence