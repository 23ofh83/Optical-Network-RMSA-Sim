from pathlib import Path
from main import build_topology, run_simulation

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"

def test_run_simulation_returns_expected_schema():
    graph = build_topology(DATA_DIR / "Network Italian 10-node"/ "IT10-topology.txt")
    # 确保读取 config 兼容或直接传入单次仿真
    result = run_simulation(
        graph,
        DATA_DIR / "Network Italian 10-node" / "IT10-matrix-1.txt",
        algorithm_type="Benchmark",
        order_descending=False,
    )

    expected_keys = {
        "total",
        "alloc",
        "blk",
        "bp",
        "noc",
        "rss",
        "highest_fsu",
        "total_fsu",
        "avg_len",
        "cost",
        "runtime_sec" # 对齐你新加的执行时间指标
    }

    assert expected_keys <= set(result)
    assert result["total"] == result["alloc"] + result["blk"]
    assert 0 <= result["bp"] <= 100
    assert result["highest_fsu"] >= -1


def test_custom_algorithm_reduces_g17_m5_desc_blocking_probability():
    graph = build_topology(DATA_DIR / "Network Germany 17-node"/ "G17-topology.txt")
    traffic_file = DATA_DIR / "Network Germany 17-node" / "G17-matrix-5.txt"

    benchmark = run_simulation(
        graph,
        traffic_file,
        algorithm_type="Benchmark",
        order_descending=True,
    )
    custom = run_simulation(
        graph,
        traffic_file,
        algorithm_type="Custom(NoC-aware Best-Fit)",
        order_descending=True,
    )

    # 验证核心算法逻辑是否依然保持预期的收敛质量
    assert custom["bp"] < benchmark["bp"]