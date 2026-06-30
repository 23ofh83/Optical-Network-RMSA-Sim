import pandas as pd
import networkx as nx
import math
import os
from itertools import islice
import logging
import time
import matplotlib
import json
matplotlib.use('Agg')
from visualization import plot_spectrum_heatmap, draw_topology_with_path

logging.basicConfig(
    level=logging.INFO, # 控制打印级别 (DEBUG, INFO, WARNING, ERROR)
    format='%(asctime)s [%(levelname)s] (%(filename)s:%(lineno)d) - %(message)s',
    handlers=[
        logging.FileHandler("simulation.log", mode='w', encoding='utf-8'), # 写入文件
        #logging.StreamHandler() # 同时打印到控制台
    ]
)

MODULATIONS = [
    {"name": "DP-16QAM",    "max_length": 500,  "capacity": 400, "slots": 6, "cost": 3.7},  
    {"name": "SC-DP-16QAM", "max_length": 700,  "capacity": 200, "slots": 3, "cost": 2.0},  
    {"name": "SC-DP-QPSK",  "max_length": 2000, "capacity": 100, "slots": 3, "cost": 1.5}   
]

NUM_SLOTS = 320  

def build_topology(file_path):
    try:
        df = pd.read_csv(file_path, sep=r'\s+', header=None, engine='python', skiprows=1)
    except Exception as e:
        logging.exception("Failed to build topology")
        return None

    G = nx.DiGraph() 
    for index, row in df.iterrows():
        source = str(int(row[3]))      
        target = str(int(row[4]))      
        distance = float(row[5])       
        G.add_edge(source, target, weight=distance) 
        G.add_edge(target, source, weight=distance) 
    logging.info(f"Topology successfully built from {os.path.basename(file_path)}. Nodes: {G.number_of_nodes()}, Edges: {G.number_of_edges()}")
    return G

def initialize_spectrum(G, num_slots=NUM_SLOTS):
    for u, v in G.edges():
        G[u][v]['spectrum'] = [0] * num_slots

def load_traffic_matrix(file_path):
    try:
        df = pd.read_csv(file_path, sep=r'\s+', header=None, engine='python')
    except Exception as e:
        return []

    requests = []
    request_id_counter = 0
    MAX_LIGHTPATH_CAPACITY = 400.0
    for i in range(df.shape[0]):
        for j in range(df.shape[1]):
            raw_bitrate = df.iloc[i, j]
            if raw_bitrate > 0 and i != j:
                total_bitrate = float(raw_bitrate) * 10.0 # 转换单位为 Gbps [cite: 461]
                
                # 🛡️ 严格对齐任务书：若超出 400G 限制，切分为多条并行的独立光通路请求 
                remaining = total_bitrate
                while remaining > 0:
                    chunk_size = min(remaining, MAX_LIGHTPATH_CAPACITY)
                    requests.append({
                        "id": request_id_counter,
                        "source": str(i + 1),
                        "destination": str(j + 1),
                        "bitrate": chunk_size
                    })
                    request_id_counter += 1
                    remaining -= chunk_size
    return requests

def get_k_shortest_paths(G, source, destination, k=5):
    try:
        paths_gen = nx.shortest_simple_paths(G, source=source, target=destination, weight='weight')
        paths = list(islice(paths_gen, k))
        paths_info = []
        for p in paths:
            distance = sum(G[p[i]][p[i+1]]['weight'] for i in range(len(p)-1))
            paths_info.append({'path': p, 'distance': distance})
        return paths_info
    except nx.NetworkXNoPath:
        return []

def get_disjoint_path_pair(G, src, dst):
    try:
        path1 = nx.shortest_path(G, src, dst, weight='weight')
        G_temp = G.copy() 
        for i in range(len(path1) - 1):
            G_temp.remove_edge(path1[i], path1[i+1])
        path2 = nx.shortest_path(G_temp, src, dst, weight='weight')

        len1 = sum(G[path1[i]][path1[i+1]]['weight'] for i in range(len(path1)-1))
        len2 = sum(G[path2[i]][path2[i+1]]['weight'] for i in range(len(path2)-1))
        return [(path1, len1), (path2, len2)]
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return []

def select_modulation(distance):
    for modulation in MODULATIONS:
        if distance <= modulation["max_length"]:
            return modulation
    return None  

def calculate_required_slots(bitrate, modulation):
    num_subcarriers = math.ceil(bitrate / modulation['capacity'])
    return num_subcarriers * modulation['slots']

def find_first_fit_slot(G, path, slots_needed):
    for start_index in range(NUM_SLOTS - slots_needed + 1):
        is_available = True  
        for i in range(len(path) - 1):
            u = path[i]
            v = path[i+1]
            if 1 in G[u][v]['spectrum'][start_index : start_index + slots_needed]:
                is_available = False  
                break    
        if is_available:
            return start_index
    return None

def find_all_available_slots(G, path, slots_needed):
    available_slots = []
    for start_index in range(NUM_SLOTS - slots_needed + 1):
        is_available = True  
        for i in range(len(path) - 1):
            u = path[i]
            v = path[i+1]
            if 1 in G[u][v]['spectrum'][start_index : start_index + slots_needed]:
                is_available = False  
                break    
        if is_available:
            available_slots.append(start_index)
    return available_slots

def allocate_slots(G, path, start_index, slots_needed):
    for i in range(len(path) - 1):
        G[path[i]][path[i+1]]['spectrum'][start_index:start_index+slots_needed] = [1]*slots_needed

def deallocate_slots(G, path, start_index, slots_needed):
    for i in range(len(path) - 1):
        G[path[i]][path[i+1]]['spectrum'][start_index:start_index+slots_needed] = [0]*slots_needed

def calculate_total_noc(G):
    total_noc = 0
    for u, v in G.edges():
        spectrum = G[u][v]['spectrum']
        for i in range(len(spectrum) - 1):
            if spectrum[i] != spectrum[i+1]:
                total_noc += 1
    return total_noc // 2

def calculate_path_noc(G, path):
    path_noc = 0
    for i in range(len(path) - 1):
        u = path[i]
        v = path[i+1]
        spectrum = G[u][v]['spectrum']
        for j in range(len(spectrum) - 1):
            if spectrum[j] != spectrum[j+1]:
                path_noc += 1
    return path_noc

def calculate_highest_used_fsu(G):
    highest_idx = -1
    for u, v in G.edges():
        spectrum = G[u][v]['spectrum']
        for i in range(len(spectrum) - 1, -1, -1):
            if spectrum[i] == 1:
                if i > highest_idx:
                    highest_idx = i
                break
    return highest_idx

def calculate_rss(G):
    total_rss = 0
    for u, v in G.edges():
        spectrum = G[u][v]['spectrum']
        free_blocks = []
        current_block = 0
        for slot in spectrum:
            if slot == 0: current_block += 1
            else:
                if current_block > 0:
                    free_blocks.append(current_block)
                    current_block = 0
        if current_block > 0:
            free_blocks.append(current_block)
        
        link_rss = math.sqrt(sum(b**2 for b in free_blocks))
        total_rss += link_rss

    return total_rss / 2

def serve_request_benchmark(G, paths_info, req):
    if not paths_info: 
        return False, [], "No Candidate Paths"
    
    p_info = paths_info[0]
    path = p_info['path']
    mod = select_modulation(p_info['distance'])
    if not mod: 
        return False, [], "Distance Exceeds Modulation Limit" # 【精准原因 1】
    
    remaining_bitrate = req["bitrate"]
    max_capacity = mod['capacity']
    allocated_chunks = []
    
    while remaining_bitrate > 0:
        chunk = min(remaining_bitrate, max_capacity)
        req_slots = calculate_required_slots(chunk, mod)
        start_slot = find_first_fit_slot(G, path, req_slots)
        
        if start_slot is not None:
            allocate_slots(G, path, start_slot, req_slots)
            allocated_chunks.append((path, start_slot, req_slots, mod['cost'], len(path)-1))
            remaining_bitrate -= chunk
        else:
            # 回滚
            for b_path, s_slot, r_slots, _, _ in allocated_chunks:
                deallocate_slots(G, b_path, s_slot, r_slots)
            return False, [], "Spectrum Fragmentation (No contiguous slots)" # 【精准原因 2】
            
    return True, allocated_chunks, "Success"

def serve_request_custom(G, paths_info, req):
    if not paths_info: return False, [],"No Candidate Paths"
    p_info = paths_info[0]
    path = p_info['path']
    mod = select_modulation(p_info['distance'])
    if not mod: 
        return False, [], "Distance Exceeds Modulation Limit" # 【精准原因 1】

    remaining_bitrate = req["bitrate"]
    allocated_chunks = [] 
    
    while remaining_bitrate > 0:
        best_chunk_path_idx = -1
        best_chunk_start_slot = -1
        best_chunk_req_slots = -1
        best_chunk_size = 0
        best_mod_cost = 0
        best_hops = 0
        min_noc = float('inf')
        
        for i, p_info in enumerate(paths_info):
            path = p_info['path']
            mod = select_modulation(p_info['distance'])
            if not mod: continue 
                
            max_capacity = mod['capacity']
            chunk_size = min(remaining_bitrate, max_capacity)
            if chunk_size <= 0:
                return False, [], "Invalid Traffic Chunk Allocation" 
            req_slots = calculate_required_slots(chunk_size, mod)
            
            valid_slots = find_all_available_slots(G, path, req_slots)
            
            for start_slot in valid_slots:
                allocate_slots(G, path, start_slot, req_slots)
                current_noc = calculate_path_noc(G, path) 
                logging.debug(f"Req {req['id']} trying Path: {path}, Slot: {start_slot}, Current NoC: {current_noc}")
                if current_noc < min_noc:
                    min_noc = current_noc
                    best_chunk_path_idx = i
                    best_chunk_start_slot = start_slot
                    best_chunk_req_slots = req_slots
                    best_chunk_size = chunk_size
                    best_mod_cost = mod['cost']
                    best_hops = len(path) - 1 
                    
                deallocate_slots(G, path, start_slot, req_slots)
                
        if best_chunk_path_idx != -1:
            best_path = paths_info[best_chunk_path_idx]['path']
            allocate_slots(G, best_path, best_chunk_start_slot, best_chunk_req_slots)
            allocated_chunks.append((best_path, best_chunk_start_slot, best_chunk_req_slots, best_mod_cost, best_hops))
            remaining_bitrate -= best_chunk_size
        else:
            for b_path, s_slot, r_slots, _, _ in allocated_chunks:
                deallocate_slots(G, b_path, s_slot, r_slots)
            return False, [],"Spectrum Fragmentation (No contiguous slots)" # 【精准原因 2】
            
    return True, allocated_chunks,"Success"
    
def serve_request_protection(G, req):
    paths_pair = get_disjoint_path_pair(G, req['source'], req['destination'])
    if not paths_pair: 
        return False, [], "No Disjoint Candidate Paths" # 加上原因
        
    p1_path, p1_len = paths_pair[0]
    p2_path, p2_len = paths_pair[1]
    
    mod1 = select_modulation(p1_len)
    mod2 = select_modulation(p2_len)
    if not mod1 or not mod2: 
        return False, [], "Distance Exceeds Protection Modulation Limit" # 加上原因
    
    remaining_bitrate = req["bitrate"]
    allocated_chunks = []
    
    max_capacity = min(mod1['capacity'], mod2['capacity'])
    
    while remaining_bitrate > 0:
        chunk = min(remaining_bitrate, max_capacity)
        req_slots1 = calculate_required_slots(chunk, mod1)
        req_slots2 = calculate_required_slots(chunk, mod2)
        
        start1 = find_first_fit_slot(G, p1_path, req_slots1)
        start2 = find_first_fit_slot(G, p2_path, req_slots2)
        
        if start1 is not None and start2 is not None:
            allocate_slots(G, p1_path, start1, req_slots1)
            allocate_slots(G, p2_path, start2, req_slots2)
            
            allocated_chunks.append((p1_path, start1, req_slots1, mod1['cost'], len(p1_path)-1))
            allocated_chunks.append((p2_path, start2, req_slots2, mod2['cost'], len(p2_path)-1))
            remaining_bitrate -= chunk
        else:
            for b_path, s_slot, r_slots, _, _ in allocated_chunks:
                deallocate_slots(G, b_path, s_slot, r_slots)
            return False, [], "Spectrum Fragmentation on Working/Protection Paths" # 加上原因
            
    return True, allocated_chunks,"Success"

def run_simulation(G_clean, traffic_file, algorithm_type, order_descending):
    G = G_clean.copy()
    initialize_spectrum(G)
    
    requests = load_traffic_matrix(traffic_file)
    requests = sorted(requests, key=lambda x: x['bitrate'], reverse=order_descending)
    
    total_reqs = len(requests)
    allocated_count = 0
    total_transponder_cost = 0
    total_path_length = 0
    total_chunks = 0

    block_reason_counts = {
        "No Candidate Paths": 0,
        "Distance Exceeds Modulation Limit": 0,
        "Spectrum Fragmentation (No contiguous slots)": 0
    }

    start_time = time.perf_counter()
    
    for req in requests:
        if algorithm_type == '1+1 Protection (First-Fit)':
            success, chunks_info, reason = serve_request_protection(G, req)
        else:
            paths_info = get_k_shortest_paths(G, req["source"], req["destination"], k=5)
            if algorithm_type == 'Benchmark':
                success, chunks_info, reason = serve_request_benchmark(G, paths_info, req)
            else:
                success, chunks_info, reason = serve_request_custom(G, paths_info, req)
            
        if success: 
            allocated_count += 1
            for chunk in chunks_info:
                total_transponder_cost += chunk[3]  
                total_path_length += chunk[4]
                total_chunks += 1
        else:
            logging.warning(
                f"[BLOCKING] Req {req['id']} ({req['source']}->{req['destination']}) "
                f"Bitrate: {req['bitrate']}G failed on {algorithm_type}. Reason: {reason}"
            )
            if reason in block_reason_counts:
                block_reason_counts[reason] += 1

    end_time = time.perf_counter()
    execution_time = end_time - start_time

    blocked_count = total_reqs - allocated_count
    blocking_ratio = (blocked_count / total_reqs) * 100 if total_reqs > 0 else 0
    final_noc = calculate_total_noc(G)
    avg_rss = calculate_rss(G)
    highest_fsu = calculate_highest_used_fsu(G)
    
    total_fsu = 0
    num_edges = G.number_of_edges()
    for u, v in G.edges():
        total_fsu += sum(G[u][v]['spectrum'])
    total_fsu = total_fsu // 2 
    
    if blocked_count > 0:
        logging.info(f"[{algorithm_type}] Simulation Finished. Total Blocked: {blocked_count}. "
                     f"Breakdown: {block_reason_counts}")
        
    avg_path_len = total_path_length / total_chunks if total_chunks > 0 else 0
    if "5" in os.path.basename(traffic_file):
        order_str = "Desc" if order_descending else "Asc"
        net_name = "UnknownNet"
        for potential_name in ["G17", "IT10", "G50"]:
            if potential_name.lower() in traffic_file.lower():
                net_name = potential_name
                break
        
        # 清洗算法名字，去掉括号
        clean_algo = algorithm_type.split('(')[0].strip()
        
        image_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "plots")
        os.makedirs(image_dir, exist_ok=True)
        
        file_name = f"{net_name}_M5_{clean_algo}_{order_str}.png"
        full_save_path = os.path.join(image_dir, file_name)
        
        plot_title = f"{net_name} Topology - Matrix 5\n{algorithm_type} ({order_str})"
        
        # 调用已经支持 save_path 的新函数！
        plot_spectrum_heatmap(G, title=plot_title, save_path=full_save_path)

    # logging.info(f"Scenario [Net:{G_clean}, Algo:{algorithm_type}] completed. "
    #              f"Blocking Ratio: {blocking_ratio:.2f}%, "
    #              f"Execution Time: {execution_time:.4f} seconds.")
    
    return {
        "total": total_reqs, "alloc": allocated_count, "blk": blocked_count, 
        "bp": blocking_ratio, "noc": final_noc, "rss": avg_rss,
        "runtime_sec": round(execution_time, 4),
        "highest_fsu": highest_fsu, "total_fsu": total_fsu, 
        "avg_len": avg_path_len, "cost": total_transponder_cost
    }


if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(current_dir, "config.json")
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        logging.info(f"成功加载外部控制配置: {config_path}")
    else:
        logging.warning("未找到 config.json，将启用系统默认保守配置运行。")
        # 兜底默认配置
        config = {
            "active_networks": ["G17"],
            "active_algorithms": ["Benchmark"],
            "traffic_matrix_indices": [1],
            "request_orders": [{"name": "Desc", "descending": true}]
        }

    all_networks = {
        "G17": {
            "name": "G17",  
            "sub_dir": "Network Germany 17-node",  # 对应实际的文件夹名
            "topo": "G17-topology.txt",  
            "matrix_prefix": "G17-matrix-{}.txt"
        },
        "IT10": {
            "name": "IT10", 
            "sub_dir": "Network Italian 10-node",  # 对应实际的文件夹名
            "topo": "IT10-topology.txt", 
            "matrix_prefix": "IT10-matrix-{}.txt"
        },
        "G50": {
        "name": "G50", 
        "sub_dir": "Network Germany 50-node",
        "topo": "G50-topology.txt",  
        "matrix_prefix":"G50-matrix-{}.txt"
    }
    }
    
    networks_to_run = [all_networks[net] for net in config["active_networks"] if net in all_networks]
    algorithms = config["active_algorithms"]
    orders = [(order["name"], order["descending"]) for order in config["request_orders"]]
    matrix_indices = config["traffic_matrix_indices"]
    all_results = [] 
    logging.info("=== Starting Optical Network RMSA Validation Framework ===")
    print("="*175) # 把总长度拉长一点，原先是 160
    print(f"{'Net':<5} | {'Mat':<5} | {'Algorithm':<26} | {'Alloc/Blk':<8} | {'BP(%)':<6} | {'HighFSU':<7} | {'TotalFSU':<8} | {'AvgHop':<7} | {'Cost':<7} | {'RSS':<6} | {'NoC':<6} | {'Time(s)':<8}")
    print("-" * 175)

    for network in networks_to_run:
        logging.info(f"Processing network topology: {network['name']}")
        topology_file = os.path.join(current_dir, "data", network["sub_dir"], network["topo"])
        base_graph = build_topology(topology_file)
        if not base_graph: continue

        for i in matrix_indices:
            traffic_file = os.path.join(current_dir, "data", network["sub_dir"], network["matrix_prefix"].format(i))
            if not os.path.exists(traffic_file): continue
                
            for algo in algorithms:
                for order_name, is_desc in orders:
                    try:
                        res = run_simulation(base_graph, traffic_file, algo, is_desc)
                    
                        print(f"{network['name']:<5} | M{i:<4} | {algo:<26} | {res['alloc']}/{res['blk']:<9} | {res['bp']:<6.2f} | {res['highest_fsu']:<7} | {res['total_fsu']:<8} | {res['avg_len']:<7.1f} | {res['cost']:<7.1f} | {res['rss']:<6.1f} | {res['noc']:<6}| {res['runtime_sec']:<8.4f}")
                    except Exception as err:
                        # 如果某一组场景崩了，打印错误并继续跑下一组，不至于让整个 IT10 的数据断流
                        logging.error(f"【运行崩溃】拓扑:{network['name']}, 算法:{algo}, 排序:{order_name} 失败！原因: {err}", exc_info=True)
                        continue
                    row_data = {
                        "Network": network['name'],
                        "Matrix": f"M{i}",
                        "Algorithm": algo,
                        "Order": order_name,
                        "Allocated": res['alloc'],
                        "Blocked": res['blk'],
                        "BP(%)": round(res['bp'], 2),
                        "HighestFSU": res['highest_fsu'],
                        "TotalFSU": res['total_fsu'],
                        "AvgHops": round(res['avg_len'], 2),
                        "Cost": round(res['cost'], 1),
                        "RSS": round(res['rss'], 1),
                        "NoC": res['noc'],  
                        "Runtime_Sec": res['runtime_sec'],
                        "Fail_No_Path": res.get("fail_reasons", {}).get("No Candidate Paths", 0),
                        "Fail_Distance": res.get("fail_reasons", {}).get("Distance Exceeds Modulation Limit", 0),
                        "Fail_Fragmentation": res.get("fail_reasons", {}).get("Spectrum Fragmentation (No contiguous slots)", 0)
                    }
                    all_results.append(row_data)
                    
        if network != networks_to_run[-1]:
            print("-" * 160)
    
    print("="*175)

    df = pd.DataFrame(all_results)
    output_path = os.path.join(current_dir, "my_simulation_results.csv")
    df.to_csv(output_path, index=False)
    logging.info(f"=== Simulation complete. Results saved to {output_path} ===")
    print(f"\n🎉 csv file: {output_path}")
