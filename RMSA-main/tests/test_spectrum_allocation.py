import networkx as nx

from main import (
    allocate_slots,
    calculate_required_slots,
    deallocate_slots,
    find_first_fit_slot,
    initialize_spectrum,
    select_modulation,
)


def make_line_graph():
    graph = nx.DiGraph()
    graph.add_edge("1", "2", weight=100)
    graph.add_edge("2", "3", weight=100)
    initialize_spectrum(graph)
    return graph


def test_select_modulation_respects_distance_limits():
    assert select_modulation(500)["name"] == "DP-16QAM"
    assert select_modulation(700)["name"] == "SC-DP-16QAM"
    assert select_modulation(2000)["name"] == "SC-DP-QPSK"
    assert select_modulation(2001) is None


def test_calculate_required_slots_rounds_up_subcarriers():
    modulation = {"capacity": 100, "slots": 3}

    assert calculate_required_slots(100, modulation) == 3
    assert calculate_required_slots(101, modulation) == 6


def test_allocate_and_deallocate_slots_on_path():
    graph = make_line_graph()
    path = ["1", "2", "3"]

    allocate_slots(graph, path, start_index=4, slots_needed=3)
    assert graph["1"]["2"]["spectrum"][4:7] == [1, 1, 1]
    assert graph["2"]["3"]["spectrum"][4:7] == [1, 1, 1]

    deallocate_slots(graph, path, start_index=4, slots_needed=3)
    assert graph["1"]["2"]["spectrum"][4:7] == [0, 0, 0]
    assert graph["2"]["3"]["spectrum"][4:7] == [0, 0, 0]


def test_first_fit_skips_occupied_slots():
    graph = make_line_graph()
    path = ["1", "2", "3"]

    allocate_slots(graph, path, start_index=0, slots_needed=5)

    assert find_first_fit_slot(graph, path, slots_needed=2) == 5
