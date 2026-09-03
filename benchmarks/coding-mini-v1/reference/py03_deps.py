import heapq


def resolve_order(graph):
    # Collect all unique nodes (both keys and elements in dependency iterables)
    all_nodes = set(graph.keys())
    for deps in graph.values():
        for d in deps:
            all_nodes.add(d)

    # Build dependency graph: dep -> list of nodes that depend on dep
    # in_degree[u]: number of unique dependencies u requires that haven't been emitted yet
    dependents = {u: [] for u in all_nodes}
    in_degree = {u: 0 for u in all_nodes}

    for u in all_nodes:
        # Deduplicate dependencies of node u
        raw_deps = graph.get(u, ())
        unique_deps = set(raw_deps)
        if u in unique_deps:
            raise ValueError(f"Self-cycle detected for node {u}")
        in_degree[u] = len(unique_deps)
        for d in unique_deps:
            dependents[d].append(u)

    # Min-heap of available nodes with in_degree == 0
    available = [u for u, deg in in_degree.items() if deg == 0]
    heapq.heapify(available)

    result = []
    while available:
        curr = heapq.heappop(available)
        result.append(curr)
        for dep_node in dependents[curr]:
            in_degree[dep_node] -= 1
            if in_degree[dep_node] == 0:
                heapq.heappush(available, dep_node)

    if len(result) != len(all_nodes):
        raise ValueError("Cycle detected in dependency graph")

    return result
