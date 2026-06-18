import matplotlib.pyplot as plt
import networkx as nx
import numpy as np


def plot_spectrum_heatmap(G, title="Spectrum Utilization"):
    """Plot spectrum occupancy across all network links."""
    edges = list(G.edges())
    num_edges = len(edges)
    num_slots = len(G[edges[0][0]][edges[0][1]]["spectrum"])

    spectrum_matrix = np.zeros((num_edges, num_slots))
    edge_labels = []

    for i, (u, v) in enumerate(edges):
        spectrum_matrix[i, :] = G[u][v]["spectrum"]
        edge_labels.append(f"{u}-{v}")

    plt.figure(figsize=(15, 8))
    plt.imshow(spectrum_matrix, aspect="auto", cmap="Reds", interpolation="nearest")
    plt.title(title, fontsize=16)
    plt.xlabel("Frequency Slots (Index)", fontsize=12)
    plt.ylabel("Network Links (Source-Dest)", fontsize=12)
    plt.yticks(range(num_edges), edge_labels, fontsize=8)

    colorbar = plt.colorbar()
    colorbar.set_label("Occupancy (1=Used, 0=Free)")

    plt.tight_layout()
    plt.show()


def draw_topology_with_path(G, path=None):
    """Draw the network topology and optionally highlight a selected path."""
    plt.figure(figsize=(10, 8))
    pos = nx.spring_layout(G, seed=42)

    nx.draw(
        G,
        pos,
        with_labels=True,
        node_color="lightblue",
        node_size=600,
        edge_color="lightgray",
        width=2,
    )

    if path:
        path_edges = list(zip(path, path[1:]))
        nx.draw_networkx_edges(G, pos, edgelist=path_edges, edge_color="red", width=4)
        nx.draw_networkx_nodes(G, pos, nodelist=path, node_color="orange", node_size=600)

    plt.title(f"Topology View {'(Red = Selected Path)' if path else ''}")
    plt.show()
