# SSH/SCP-Based Distributed Implementation

This is an **alternative implementation** using SSH and SCP for real distributed processing on Jetstream2 cloud infrastructure. This is completely separate from the main thread-based implementation.

## Key Differences from Main Implementation

- **Architecture**: SSH/SCP-based (real remote execution)
- **Target**: Jetstream2 cloud VMs only (won't run locally)
- **Communication**: SSH commands between master and workers
- **Data Transfer**: SCP file transfers over network
- **Complexity**: Simpler, minimal dependencies
- **Dependencies**: None (pure Python + FFmpeg)

## Structure

```
distributed-ssh-implementation/
├── framework/
│   └── src/
│       ├── main.py              # CLI entry point
│       └── core/
│           ├── segmenter.py     # Video splitting
│           ├── processor.py     # FFmpeg processing
│           ├── merger.py        # Video merging
│           ├── dynamic_processor.py    # Dynamic scheduling via SSH
│           └── distributed_processor.pyd  # Static distribution via SSH
├── benchmark.py                 # Benchmark runner
└── benchmark_results.csv        # Actual benchmark results from cloud runs
```

## Benchmark Results

Results from actual Jetstream2 cloud deployment:

| Video Size | Strategy | Runtime (seconds) |
|-----------|----------|------------------|
| 24s | Single | 1.1 |
| 24s | Static | 5.2 |
| 24s | Dynamic | 2.47 |
| 120s | Single | 4.5 |
| 120s | Static | 26.11 |
| 120s | Dynamic | 13.24 |
| Full | Single | 15.36 |
| Full | Static | 90.02 |
| Full | Dynamic | 45.89 |

**Key Insight**: Static partitioning shows significant overhead from SSH/SCP transfers, but dynamic scheduling still outperforms it, validating our core hypothesis.

## How to Use

**Prerequisites:**
- Jetstream2 VMs (1 master + workers)
- SSH access configured between nodes
- FFmpeg installed on all nodes

**Run:**
```bash
cd distributed-ssh-implementation
python3 framework/src/main.py --input video.mp4 --output result.mp4 --strategy dynamic
```

**Run Benchmark:**
```bash
python3 benchmark.py
```

## When to Use This vs Main Implementation

**Use this SSH/SCP implementation when:**
- Testing on actual Jetstream2 cloud infrastructure
- Need real network-based distribution
- Testing large-scale scenarios with many VMs
- Measuring real network overhead

**Use main implementation (thread-based) when:**
- Local development and testing
- Need comprehensive metrics and visualizations
- Rapid prototyping
- Presentation and demonstration
- Don't have cloud infrastructure access

## Note

This implementation is provided as an alternative approach and for comparative analysis. The main thread-based implementation in the root directory is the primary, feature-complete implementation with comprehensive metrics, logging, and visualization capabilities.
