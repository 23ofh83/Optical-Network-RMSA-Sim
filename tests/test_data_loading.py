from pathlib import Path

from main import build_topology, load_traffic_matrix


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"


def test_build_topology_loads_bidirectional_graph():
    graph = build_topology(DATA_DIR / "Network Italian 10-node" / "IT10-topology.txt")

    assert graph is not None
    assert graph.number_of_nodes() > 0
    assert graph.number_of_edges() > 0

    source, target = next(iter(graph.edges()))
    assert graph.has_edge(target, source)
    assert "weight" in graph[source][target]
    assert graph[source][target]["weight"] > 0


def test_load_traffic_matrix_returns_valid_requests():
    requests = load_traffic_matrix(DATA_DIR / "Network Italian 10-node" / "IT10-matrix-1.txt")

    assert len(requests) == 58
    assert all(req["source"] != req["destination"] for req in requests)
    assert all(req["bitrate"] > 0 for req in requests)
    assert {"id", "source", "destination", "bitrate"} <= set(requests[0])
