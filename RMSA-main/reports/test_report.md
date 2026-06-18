# Validation Report

## Scope

This report summarizes validation coverage for the optical network RMSA
simulation project. The goal is to verify data loading, spectrum allocation,
algorithm execution, and result consistency for repeatable evaluation.

## Test Environment

- Language: Python
- Main libraries: NetworkX, Pandas, NumPy, Matplotlib
- Test framework: pytest
- Input data: optical network topology files and traffic matrices

## Validation Scenarios

- 2 topologies: Germany 17-node and Italian 10-node
- 5 traffic matrices per topology
- 3 algorithms
- 2 request ordering strategies
- 60 total simulation result rows

## Automated Regression Checks

- Topology files load into non-empty bidirectional graphs.
- Traffic matrices generate valid source-destination requests.
- Modulation selection respects distance limits.
- Slot calculation rounds up required subcarriers.
- Allocation and deallocation update spectrum state correctly.
- First-Fit search skips occupied spectrum slots.
- Simulation output contains required metrics.
- Blocking probability stays within the valid 0-100% range.

## Test Coverage Matrix

| Area | Test Purpose | Validation Type |
| --- | --- | --- |
| Topology loading | Verify topology files create non-empty bidirectional graphs | Functional |
| Traffic loading | Verify matrix files generate valid traffic requests | Functional |
| Modulation selection | Verify distance thresholds map to expected modulation formats | Boundary |
| Slot calculation | Verify bitrate-to-slot conversion rounds up correctly | Boundary |
| Spectrum allocation | Verify allocation and deallocation update link state | State |
| First-Fit search | Verify occupied slots are skipped | Functional |
| Simulation output | Verify required metrics and blocking probability range | Regression |
| Algorithm comparison | Verify custom strategy reduces G17 M5 descending blocking probability | Regression |

## Key Result

For the G17 topology with matrix 5 and descending request order, the custom
NoC-aware Best-Fit strategy reduced blocking probability from 20.96% to 6.25%
compared with the benchmark First-Fit approach.

## Known Limitations

- The project is an academic simulation, not a production network controller.
- Tests currently focus on deterministic functional behavior and output
  consistency, not large-scale performance benchmarking.
- Additional CI-generated reports can be added after publishing the project to
  GitHub.
