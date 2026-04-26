# Elastic Distributed Video Processing Framework

A distributed video processing system with dynamic workload partitioning, implemented using a master-worker architecture on Jetstream2.

## Team Members

- Anuj Prakash
- Arun Munagala
- Shreyas Amit Dhekane

---

## Features

- Master-worker architecture using SSH/SCP communication
- Multiple workload strategies (single, static, dynamic)
- FFmpeg-based video processing
- Dynamic scheduling with parallel execution
- Retry-based fault tolerance
- Benchmarking and performance comparison

---

## Prerequisites

### Local Development

```bash
# Install FFmpeg
brew install ffmpeg

# Python (no external dependencies required)
```

### Cloud Deployment (Jetstream2)

- Jetstream2 instances (1 master + workers)
- SSH access configured between nodes
- Python 3 installed on all nodes
- FFmpeg installed on all nodes

---

## Project Structure

```
framework/
├── src/
│   ├── main.py                    # CLI entry point
│   ├── core/
│   │   ├── segmenter.py           # Video splitting
│   │   ├── processor.py           # Single-node processing
│   │   ├── merger.py              # Video merging
│   │   ├── static_processor.py
│   │   ├── dynamic_processor.py
│   │   └── distributed_processor.py
├── benchmark.py                   # Benchmark script
├── benchmark_results.csv          # Results
├── input/                         # Input videos (not tracked)
├── output/                        # Outputs (not tracked)
└── README.md
```

---

## Quick Start

### Single-node baseline

```bash
PYTHONPATH=src python3 src/main.py \
  --input input/test_24sec.mp4 \
  --output output/single.mp4 \
  --strategy single
```

### Static distributed

```bash
PYTHONPATH=src python3 src/main.py \
  --input input/test_24sec.mp4 \
  --output output/static.mp4 \
  --strategy static
```

### Dynamic distributed

```bash
PYTHONPATH=src python3 src/main.py \
  --input input/test_24sec.mp4 \
  --output output/dynamic.mp4 \
  --strategy dynamic
```

---

## Benchmarking

Run all strategies across different input sizes:

```bash
python3 benchmark.py
```

---

## Results

| Input         | Single | Static  | Dynamic |
|---------------|--------|---------|---------|
| 24s           | 1.1s   | 5.2s    | 2.47s   |
| 120s          | 4.5s   | 26.1s   | 13.2s   |
| Full (~6m44s) | 15.3s  | 90.0s   | 45.8s   |

---

## Key Observations

- Single-node is fastest for small inputs due to low overhead
- Static scheduling performs worst due to poor load balancing
- Dynamic scheduling improves over static but is still slower than single
- SCP-based file transfer introduces significant overhead
- Distributed processing becomes more meaningful as workload increases

---

## Fault Tolerance

The system includes retry-based fault tolerance:

- If a worker fails, the task is retried on another worker
- Ensures pipeline completion without manual intervention
- Failure simulation tested using invalid worker nodes

---

## Architecture

### Master Node

- Splits input video into chunks
- Assigns tasks to workers
- Collects processed outputs
- Merges final video

### Worker Nodes

- Receive chunks via SCP
- Process using FFmpeg
- Send results back to master

---

## Workload Strategies

1. **Single** — Sequential processing on one machine
2. **Static** — Pre-assigned chunks to workers (fixed distribution)
3. **Dynamic** — Workers process tasks in parallel with flexible scheduling

---

## Future Improvements

- Replace SCP with shared storage (NFS) to reduce overhead
- Add worker health monitoring
- Improve scheduling with real-time load tracking

---

## License

Academic project – Indiana University Bloomington
