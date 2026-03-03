from core_function import (build_topology, load_traffic_matrix, 
                            initialize_spectrum, select_modulation, 
                            calculate_required_slots, calculate_total_noc, 
                            get_shortest_path)
import networkx as nx
import matplotlib.pyplot as plt
import math
import visualization as viz
import os




def draw_topology(G):
    """
    Visualize the network topology.
    """
    plt.figure(figsize=(10, 8))
    # spring_layout provides an aesthetically balanced layout
    pos = nx.spring_layout(G, seed=42) 
    
    # Draw nodes and edges
    nx.draw(G, pos, with_labels=True, node_color='skyblue', 
            node_size=800, font_size=12, font_weight='bold', edge_color='gray')
    
    # Display edge weights (distances)
    edge_labels = nx.get_edge_attributes(G, 'weight')
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=9)
    
    plt.title("Optical Network Topology (Edge labels = Distance in km)")
    plt.show()












def find_and_allocate_slots(G, path, slots_needed):
    # Check the spectrum segment starting from start_index
    # Example: start_index = 0, slots_needed = 3 → check [0, 1, 2]
    # Outer loop: try each possible starting slot
    for start_index in range(320 - slots_needed + 1):

        is_available = True  

        # Inner loop: check each edge along the path
        for i in range(len(path) - 1):
            u = path[i]
            v = path[i+1]
            spectrum = G[u][v]['spectrum']

            # Check if any slot in the segment is occupied
            if spectrum[start_index : start_index + slots_needed].count(1) > 0:
                is_available = False  
                break    

        if is_available:
            # Allocate slots along the entire path
            for i in range(len(path) - 1):
                u = path[i]
                v = path[i+1]
                for slot in range(start_index, start_index + slots_needed):
                    G[u][v]['spectrum'][slot] = 1
            return start_index

    return None






# ==========================================
# Main program entry
# ==========================================
if __name__ == "__main__":
    

    matrix_names = ['M1', 'M2', 'M3', 'M4', 'M5']
    noc_list = []
    slots_list = []
    blocking_list = []

    # 1. Build topology
    current_dir = os.path.dirname(os.path.abspath(__file__))
    topology_file = os.path.join(current_dir, "data", "Network Italian 10-node", "IT10-topology.txt")

    # 2. Load traffic matrix
    traffic_file_total = os.path.join(current_dir, "data", "Network Italian 10-node", "IT10-matrix-{}.txt")
    network_graph = build_topology(topology_file)
    
    if network_graph:
        draw_topology(network_graph)

    orders = [
        ('Ascending', False), 
        ('Descending', True)  
    ]

    print(f"{'Matrix':<8} | {'Order':<10} | {'Reqs':<5} | {'Block':<8} | {'BP(%)':<8} | {'Highest':<8} | {'Slots':<8} | {'NoC':<5}")
    print("-" * 95)

    for i in range(1, 6):
        traffic_file = traffic_file_total.format(i)
        connection_requests = load_traffic_matrix(traffic_file)
        for order_name, reverse_flag in orders:
            initialize_spectrum(network_graph) 
            connection_requests = sorted(connection_requests, key=lambda x: x['bitrate'], reverse=reverse_flag)
            
            total_requests = len(connection_requests)
            allocated_count = 0
            benchmark_noc = 0

            for req in connection_requests:
                path, distance = get_shortest_path(network_graph, req["source"], req["destination"])
                modulation = select_modulation(distance)

                if modulation:
            
                    remaining_bitrate = req["bitrate"]
                    max_capacity = modulation['capacity'] 
                    sub_requests_sucess=True
                    while remaining_bitrate > 0 :
                        current_chunk_bitrate = min(remaining_bitrate, max_capacity)
                        required_slots = calculate_required_slots(current_chunk_bitrate, modulation)

                        start_slot = find_and_allocate_slots(network_graph, path, required_slots)

                        if start_slot is not None:
                            remaining_bitrate -= current_chunk_bitrate
                        else:
                            sub_requests_sucess=False
                            break
                    if sub_requests_sucess and remaining_bitrate <= 0:
                        allocated_count += 1
                    else:
                        pass

            blocked_count = total_requests - allocated_count
            blocking_ratio = (blocked_count / total_requests) * 100
            total_used_slots = sum(sum(data['spectrum']) for u, v, data in network_graph.edges(data=True))

            benchmark_noc = calculate_total_noc(network_graph)
            noc_list.append(benchmark_noc)
            slots_list.append(total_used_slots)
            blocking_list.append(blocking_ratio)
            highest_slot_used = 0
            for u, v, data in network_graph.edges(data=True):
                
                occupied_indices = [idx for idx, val in enumerate(data['spectrum']) if val == 1]
                if occupied_indices:
                    # Update the highest slot used across all edges
                    highest_slot_used = max(highest_slot_used, max(occupied_indices))
            print(f"{i:<8} | {order_name:<10} | {total_requests:<5} | {allocated_count}/{blocked_count:<6} | {blocking_ratio:<8.2f} | {highest_slot_used:<8} | {total_used_slots:<8} | {benchmark_noc:<5}")

            # Core feature: one-click visualization
            #print("Generating visualization...")
            viz.plot_spectrum_heatmap(network_graph, title=f"Spectrum Allocation - Matrix {i}")



