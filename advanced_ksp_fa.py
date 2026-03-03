from core_function import *
import networkx as nx
from core_function import (build_topology, load_traffic_matrix, 
                            initialize_spectrum, select_modulation, 
                            calculate_required_slots, calculate_total_noc)
import os

def k_shortest_paths(G, source, target, k):
    row_path=list(nx.shortest_simple_paths(G, source, target, weight='weight'))[:k]
    k_shortest_paths_distances=[]
    for path in row_path:
        distance=0
        for i in range(len(path)-1):
            distance+=G[path[i]][path[i+1]]['weight']
        k_shortest_paths_distances.append((path, distance))
    return k_shortest_paths_distances


def elevate_noc_increase(current_spectrum, start_lot, required_slot):
    old_noc = count_noc(current_spectrum)
    simulated_spectrum = current_spectrum.copy()
    simulated_spectrum[start_lot:start_lot+required_slot]=[1]*(required_slot)
    new_noc = count_noc(simulated_spectrum)
    return new_noc - old_noc

def count_noc(spectrum_list):
    if not spectrum_list:
        return 0
    noc = 0
    if spectrum_list[0] == 0:
        noc += 1
    for i in range(1, len(spectrum_list)):
        if spectrum_list[i] == 0 and spectrum_list[i - 1] == 1:
            noc += 1
    return noc

def find_available_slot(spectrum_list,required_slot):
    available_start=[]
    for i in range(len(spectrum_list)-required_slot+1):
        if all(slot == 0 for slot in spectrum_list[i:i+required_slot]):
            available_start.append(i)
    return available_start

def get_path_common_spectrum(G,path,num_slot=320):
    common_spectrum=[0]*num_slot
    for i in range(len(path)-1):
        link_spectrum=G[path[i]][path[i+1]]['spectrum']
        for j in range(num_slot):
            if link_spectrum[j]==1:
                common_spectrum[j]=1
    return common_spectrum

def allocate_slots(G,path,start_lot,required_slot):
    for i in range(len(path)-1):
        for j in range(start_lot, start_lot+required_slot):
            G[path[i]][path[i+1]]['spectrum'][j]=1

def deallocate_slots(G,path,start_lot,required_slot):
    for i in range(len(path)-1):
        for j in range(start_lot, start_lot+required_slot):
            G[path[i]][path[i+1]]['spectrum'][j]=0

if __name__=="__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    topology_file = os.path.join(current_dir, "data", "Network Germany 17-node", "G17-topology.txt")
    network_graph = build_topology(topology_file)

    traffic_load_total=os.path.join(current_dir, "data", "Network Germany 17-node", "G17-matrix-{}.txt")
    orders = [('Ascending', False), ('Descending', True)]

    print(f'{"Matrix":<8} | {"Order":<10} | {"Reqs":<5} | {"Block":<8} | {"BP(%)":<8}  | {"Slots":<8} | {"NoC":<5}')
    print("-"*95)

    for i in [1,3,5]:
        traffic_file=traffic_load_total.format(i)
        raw_requests=load_traffic_matrix(traffic_file)

        for orders_name, reverse_flag in orders:
            initialize_spectrum(network_graph)
            connection_requests=sorted(raw_requests, key=lambda x: x['bitrate'], reverse=reverse_flag)
            

            total_requests=len(connection_requests)
            allocated_count=0

            for req_idx,req in enumerate(connection_requests):
                remaining_bitrate=req['bitrate']
                k_path=k_shortest_paths(network_graph, req['source'], req['destination'], 5)
                best_path_id=-1
                best_allocation_plan=[]
                min_total_noc=float('inf')
                sub_requests_success=True

            

                for path_id,(path,distance) in enumerate(k_path):
                    modulation=select_modulation(distance)
                    if not modulation:
                        continue

                    remaining_bitrate=req['bitrate']
                    max_capacity=modulation['capacity']
                    temp_allocation=[]
                    success=True
                    

                    while remaining_bitrate > 0:
                        current_chunk_bitrate = min(remaining_bitrate, max_capacity)

                        required_slots=calculate_required_slots(current_chunk_bitrate, modulation)
                        common_spectrum=get_path_common_spectrum(network_graph,path)
                        available_start=find_available_slot(common_spectrum, required_slots)
                        
                        best_path=None
                        best_start_slot=None
                        min_delta_noc=float('inf')
                        best_effiency=float('inf')
                        best_path_length=float('inf')


                        for start_slot in available_start:
                            delta_noc=elevate_noc_increase(common_spectrum, start_slot, required_slots)

                            if delta_noc < min_delta_noc:
                                min_delta_noc=delta_noc
                                best_start_slot=start_slot
                        if best_start_slot is not None:
                            allocate_slots(network_graph, path, best_start_slot, required_slots)
                            temp_allocation.append((best_start_slot, required_slots))
                            remaining_bitrate -= current_chunk_bitrate
                        else:
                            success=False
                            break

                    if success:
                        current_total_noc=calculate_total_noc(network_graph)
                        if current_total_noc < min_total_noc:
                            min_total_noc=current_total_noc
                            best_path_id=path_id
                            best_allocation_plan=temp_allocation.copy()
                    for s_slot, r_slots in temp_allocation:
                        deallocate_slots(network_graph, path, s_slot, r_slots)
                        
                    
                if best_path_id != -1 and best_allocation_plan:
                    best_path = k_path[best_path_id][0]
                    for s_slot, r_slots in best_allocation_plan:
                        allocate_slots(network_graph, best_path, s_slot, r_slots)
                    allocated_count += 1

            blocked_count=total_requests-allocated_count
            bp=(total_requests-allocated_count)/total_requests*100
            total_noc=calculate_total_noc(network_graph)
          
            print(f'M{i:<7} | {orders_name:<10} | {total_requests:<5} | {allocated_count}/{blocked_count:<6} | {bp:<8.2f} |        | {total_noc:<5}')


                        
                            






