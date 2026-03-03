
import pandas as pd
import networkx as nx
import math

MODULATIONS = [
    {"name": "DP-16QAM",    "max_length": 500,  "capacity": 400, "slots": 6},
    {"name": "SC-DP-16QAM", "max_length": 700,  "capacity": 200, "slots": 3},
    {"name": "SC-DP-QPSK",  "max_length": 2000, "capacity": 100, "slots": 3}
]

def build_topology(file_path):
    """
    Read the topology txt file and generate a NetworkX graph.
    """
    print(f"Reading topology file: {file_path}")
    
    try:
        df = pd.read_csv(file_path, sep='\s+', header=None, engine='python', skiprows=1)
    except Exception as e:
        print(f"Failed to read file: {e}")
        return None

    # Print the first few rows to verify correct data loading
    print("----- Data Preview (First 3 Rows) -----")
    print(df.head(3))
    print("---------------------------------------\n")

    # 2. Create an undirected graph (optical fibers are typically bidirectional)
    G = nx.Graph()

    # 3. Iterate through each row to add nodes and edges
    # According to the PDF: column 4 (index 3) is source,
    # column 5 (index 4) is destination,
    # column 6 (index 5) is distance
    for index, row in df.iterrows():
        source = str(int(row[3]))  
        target = str(int(row[4]))
        distance = float(row[5])   
        
        # Add edge and store distance as weight (used later by Dijkstra's algorithm)
        G.add_edge(source, target, weight=distance)

    print(f"Topology successfully constructed. Contains {G.number_of_nodes()} nodes and {G.number_of_edges()} edges.")
    return G

def load_traffic_matrix(file_path):
    """
    Read the 10x10 traffic matrix file.
    Rows = source nodes, columns = destination nodes, values = bitrate.
    Note: topology nodes are labeled 1–10, while matrix indices are 0–9,
    therefore a +1 offset is required.
    """
    #print(f"Reading traffic matrix: {file_path}")
    
    try:
        df = pd.read_csv(file_path, sep='\s+', header=None, engine='python')
        
        # Ensure the matrix is 10x10
            
    except Exception as e:
        print(f"Failed to read file: {e}")
        return []

    requests = []
    request_id_counter = 0

    # Iterate through each row (source) and column (destination)
    for i in range(df.shape[0]):
        for j in range(df.shape[1]):
            bitrate = df.iloc[i, j]
            
            # Only consider valid requests (bitrate > 0 and source ≠ destination)
            if bitrate > 0 and i != j:
                source_node = str(i + 1)
                dest_node = str(j + 1)
                
                requests.append({
                    "id": request_id_counter,
                    "source": source_node,
                    "destination": dest_node,
                    "bitrate": float(bitrate)*10
                })
                request_id_counter += 1
            
    #print(f"Successfully parsed {request_id_counter} connection requests from the matrix.")
    return requests

def initialize_spectrum(G, num_slots=320):
    """
    Initialize spectrum resources for each edge in the graph.
    G[u][v]['spectrum'] is a list of length 320.
    0 indicates free, 1 indicates occupied.
    """
    for u, v in G.edges():
        # Create a zero-initialized list for each edge
        G[u][v]['spectrum'] = [0] * num_slots
        
    #print(f"Spectrum initialized with {num_slots} slots for {G.number_of_edges()} links.")

def select_modulation(distance):
    """
    Select modulation format based on transmission distance.
    """
    for modulation in MODULATIONS:
        if distance <= modulation["max_length"]:
            return modulation
    return None  

def calculate_required_slots(bitrate, modulation):
    """
    Calculate the required number of spectrum slots based on bitrate and modulation format.
    """
    if modulation is None:
        return None  
    
    num_slots = math.ceil(bitrate / modulation['capacity'])
    total_slots = num_slots * modulation['slots']
    
    return total_slots

def calculate_total_noc(G):
    total_noc = 0
    for u, v in G.edges():
        spectrum = G[u][v]['spectrum']
        for i in range(len(spectrum) - 1):
            if spectrum[i] != spectrum[i+1]:
                total_noc += 1
    return total_noc

def get_shortest_path(G, source, destination):
    try:
        # 1. Retrieve the path (list of nodes)
        path = nx.shortest_path(G, source=source, target=destination, weight='weight')
        
        # 2. Retrieve the total path length
        distance = nx.shortest_path_length(G, source=source, target=destination, weight='weight')
        
        return path, distance
    except nx.NetworkXNoPath:
        # Handle disconnected nodes
        return None, float('inf')
    