import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
import math
import visualization as viz
import os

MODULATIONS = [
    {"name": "DP-16QAM",    "max_length": 500,  "capacity": 400, "slots": 6},
    {"name": "SC-DP-16QAM", "max_length": 700,  "capacity": 200, "slots": 3},
    {"name": "SC-DP-QPSK",  "max_length": 2000, "capacity": 100, "slots": 3}
]

def build_topology(file_path):
    """
    读取拓扑 txt 文件并生成 NetworkX 图
    """
    print(f"正在读取拓扑文件: {file_path}")
    
    try:
        df = pd.read_csv(file_path, sep='\s+', header=None, engine='python', skiprows=1)
    except Exception as e:
        print(f"读取文件失败: {e}")
        return None

    # 打印前几行，检查数据有没有读错
    print("----- 数据预览 (前3行) -----")
    print(df.head(3))
    print("----------------------------\n")

    # 2. 创建一个无向图 (光纤通常是双向的)
    G = nx.Graph()

    # 3. 遍历数据行，添加节点和边
    # 根据 PDF 说明：第4列(索引3)是源，第5列(索引4)是目的，第6列(索引5)是距离 [cite: 92, 93]
    for index, row in df.iterrows():
        source = str(int(row[3]))  # 确保节点名称是字符串形式的整数
        target = str(int(row[4]))
        distance = float(row[5])   
        
        # 添加边，并将距离作为权重 (weight) 存进去，Dijkstra 算法以后要用它！
        G.add_edge(source, target, weight=distance)

    print(f"✅ 成功构建网络拓扑！包含 {G.number_of_nodes()} 个节点和 {G.number_of_edges()} 条边。")
    return G
def initialize_spectrum(G, num_slots=320):
    """
    给图中的每一条边初始化频谱资源
    G[u][v]['spectrum'] 是一个长度为 320 的列表
    0 表示空闲，1 表示占用
    """
    for u, v in G.edges():
        # 为每一条边创建一个全为 0 的列表
        G[u][v]['spectrum'] = [0] * num_slots
        
    print(f"✅ 已为 {G.number_of_edges()} 条链路初始化了 {num_slots} 个频谱槽位。")

def draw_topology(G):
    """
    把网络图画出来看看长什么样
    """
    plt.figure(figsize=(10, 8))
    # spring_layout 是一种好看的节点排列方式
    pos = nx.spring_layout(G, seed=42) 
    
    # 画节点和连线
    nx.draw(G, pos, with_labels=True, node_color='skyblue', 
            node_size=800, font_size=12, font_weight='bold', edge_color='gray')
    
    # 把距离(weight)写在连线上
    edge_labels = nx.get_edge_attributes(G, 'weight')
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=9)
    
    plt.title("Optical Network Topology (Edge labels = Distance in km)")
    plt.show()

def load_traffic_matrix(file_path):
    """
    读取 10x10 的流量矩阵文件
    行 = 源节点 (Source), 列 = 目的节点 (Destination), 值 = 比特率 (Bitrate)
    注意：因为拓扑节点是 1-10，而矩阵索引是 0-9，所以需要 +1 修正
    """
    print(f"正在读取流量矩阵: {file_path}")
    
    try:
        # 读取矩阵，假设没有表头
        df = pd.read_csv(file_path, sep='\s+', header=None, engine='python')
        
        # 确保它是 10x10 的
        if df.shape != (10, 10):
            print(f"⚠️ 警告: 矩阵形状是 {df.shape}，可能不对！预期是 (10, 10)")
            
    except Exception as e:
        print(f"读取文件失败: {e}")
        return []

    requests = []
    request_id_counter = 0

    # 遍历矩阵的每一行 (Source) 和每一列 (Destination)
    # i 是行索引 (0-9), j 是列索引 (0-9)
    for i in range(df.shape[0]):
        for j in range(df.shape[1]):
            bitrate = df.iloc[i, j] # 获取格子里的数值
            
            # 只有当流量大于 0，且源不等于目的时，才算有效请求
            if bitrate > 0 and i != j:
                # 关键步骤：把索引 0 变成节点 "1"
                source_node = str(i + 1)
                dest_node = str(j + 1)
                
                requests.append({
                    "id": request_id_counter,
                    "source": source_node,
                    "destination": dest_node,
                    "bitrate": float(bitrate)
                })
                request_id_counter += 1
            
    print(f"✅ 成功从矩阵中解析出 {request_id_counter} 条连接请求。")
    return requests

def get_shortest_path(G, source, destination):
    
    try:
        # 1. 获取路径 (返回一个节点列表，例如 ['1', '5', '2'])
        path = nx.shortest_path(G, source=source, target=destination, weight='weight')
        
        # 2. 获取路径的总长度 (返回一个浮点数，例如 350.0)
        distance = nx.shortest_path_length(G, source=source, target=destination, weight='weight')
        
        return path, distance
    except nx.NetworkXNoPath:
        # 如果两点之间不通，NetworkX 会报错，这里我们要捕获它
        return None, float('inf')
    
def select_modulation(distance):
    """
    根据距离选择调制格式
    """
    for modulation in MODULATIONS:
        if distance <= modulation["max_length"]:
            return modulation
    return None  # 如果距离超过所有调制的最大长度，返回 None

def calculate_required_slots(bitrate, modulation):
    """
    根据比特率和调制格式计算所需的频谱槽位数
    """
    if modulation is None:
        return None  # 无可用调制格式
    
    num_slots=math.ceil(bitrate/modulation['capacity'])
    total_slots=num_slots*modulation['slots']
    
    return total_slots

def find_and_allocate_slots(G,path,slots_needed):
# 我们要检查从 start_index 开始的那一段频谱
# 比如 start_index = 0, slots_needed = 3, 也就是检查 [0, 1, 2]
# 外层循环：尝试每一个可能的起始槽位 start_index
    for start_index in range(320 - slots_needed + 1):

        is_available = True  # <--- 1. 先立旗：假设这个 start_index 在所有边上都是空的

        # 内层循环：检查路径上的每一条边 (u, v)
        for i in range(len(path) - 1):
            u = path[i]
            v = path[i+1]
            spectrum = G[u][v]['spectrum']

            # 检查这条边上的 [start_index : start_index + slots_needed] 是否有 1
            if spectrum[start_index : start_index + slots_needed].count(1) > 0:
                is_available = False  # 发现有占用，倒旗
                break    

        if is_available:
            # 1. 再次遍历路径上的每一条边 u, v
            # 2. 把 G[u][v]['spectrum'] 里的那一小段 [start_index : start_index + slots_needed] 全部设为 1
            for i in range(len(path) - 1):
                u = path[i]
                v = path[i+1]
                for slot in range(start_index, start_index + slots_needed):
                    G[u][v]['spectrum'][slot] = 1
            return start_index

    return None

def calculate_total_noc(G):
    total_noc=0
    for u, v in G.edges():
        spectrum=G[u][v]['spectrum']
        for i in range(len(spectrum)-1):
            if spectrum[i]!=spectrum[i+1]:
                total_noc+=1
    return total_noc
# ==========================================
# 主程序入口 
# ==========================================
if __name__ == "__main__":
    # 1. build topology
    current_dir = os.path.dirname(os.path.abspath(__file__))
    topology_file = os.path.join(current_dir, "data", "Network Italian 10-node", "IT10-topology.txt")
    # 2.load traffic matrix
    traffic_file_total = os.path.join(current_dir, "data", "Network Italian 10-node", "IT10-matrix-{}.txt")
    network_graph = build_topology(topology_file)
    
    if network_graph:
         draw_topology(network_graph)
      
    
    for i in range(1, 6):
        initialize_spectrum(network_graph) 
        traffic_file=traffic_file_total.format(i)
        connection_requests = load_traffic_matrix(traffic_file)
        allocated_count = 0
        benchmark_noc = 0
    # 打印前 5 个需求看看对不对
    #if connection_requests:
    #    print("\n----- 转换后的请求样本 (前5个) -----")
    #        for req in connection_requests[:5]:
    #            print(req)
    #        print("------------------------------------")
        for req in connection_requests:
            path, distance = get_shortest_path(network_graph, req["source"], req["destination"])
            modulation = select_modulation(distance)
            if modulation:
                required_slots = calculate_required_slots(req["bitrate"], modulation)
                start_slot = find_and_allocate_slots(network_graph, path, required_slots)
                if start_slot is not None:
                    allocated_count += 1
                    #print(f"请求 {req['id']} (src:{req['source']}->dst:{req['destination']}): 成功分配! 调制: {modulation['name']}, 槽位: {start_slot}-{start_slot + required_slots - 1}")
                else:
                    print(f"请求 {req['id']}: 阻塞 (频谱不足)")
            else:
                print(f"请求 {req['id']}: 阻塞 (距离过长)")
        benchmark_noc = calculate_total_noc(network_graph)
        print(f"基准算法 (First Fit) 的总切割数 (NoC): {benchmark_noc}")

        # === 核心：一键可视化 ===
        print("正在生成可视化图表...")
        viz.plot_spectrum_heatmap(network_graph, title=f"Spectrum Allocation - Matrix {i}")

    #print(f"\n最终结果: 成功分配 {allocated_count} / {len(connection_requests)} 个请求")
            #print("请求 ID: {}, 从 {} 到 {}, 比特率: {}, 最短路径: {}, 距离: {}".format(
            #    req["id"], req["source"], req["destination"], req["bitrate"], path, distance
            #))
            #print("选择的调制格式: {}\n".format(modulation["name"] if modulation else "无可用调制"))
            #print("所需频谱槽位数: {}\n".format(required_slots if required_slots else "无法计算"))
