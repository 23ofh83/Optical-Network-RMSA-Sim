# Optical Network RMSA Validation Framework

Python validation project for Routing, Modulation, and Spectrum Allocation
(RMSA) strategies in elastic optical networks.

The project compares baseline and improved allocation strategies across fixed
network topologies and traffic matrices, then reports engineering metrics such
as blocking probability, spectrum usage, fragmentation, path length, and
transponder cost.

## Scope

- Load optical network topologies and traffic matrices from text files.
- Simulate routing and spectrum allocation under multiple algorithms.
- Compare benchmark First-Fit allocation against a NoC-aware Best-Fit strategy.
- Export structured simulation results to CSV.
- Validate core functions with automated regression tests.

## Algorithms

- `Benchmark`: shortest-path routing with First-Fit spectrum assignment.
- `Custom(NoC-aware Best-Fit)`: evaluates candidate paths and slot positions to
  reduce local spectrum fragmentation.
- `1+1 Protection (First-Fit)`: allocates disjoint working and protection paths.

## Validation Scenarios

The current dataset covers:

- 2 network topologies: Germany 17-node and Italian 10-node.
- 5 traffic matrices per topology.
- 3 allocation algorithms.
- 2 request ordering strategies: ascending and descending bitrate.

This produces 60 simulation result rows in `my_simulation_results.csv`.

## Metrics

- Blocking probability.
- Allocated and blocked request counts.
- Highest used frequency slot.
- Total used frequency slots.
- Average hop count.
- Transponder cost.
- RSS fragmentation metric.
- Number of Cuts (NoC).

## Key Result

On the Germany 17-node topology with traffic matrix 5 and descending request
order, the NoC-aware Best-Fit strategy reduced worst-case blocking probability
from 20.96% to 6.25% compared with the benchmark.

## Test Automation

The `tests/` directory contains pytest regression tests for:

- topology loading;
- traffic matrix parsing;
- modulation and slot calculations;
- slot allocation and deallocation;
- First-Fit slot search;
- simulation output schema and metric ranges.

Run tests:

```bash
pytest
```

Run the simulation:

```bash
python main.py
```

## Requirements

Install dependencies:

```bash
pip install -r requirements.txt
```
