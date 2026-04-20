# Elastic Distributed Video Processing Framework

A distributed video processing system with dynamic workload partitioning for cloud deployment.

## Team Members
- Anuj Prakash (asprakas@iu.edu)
- Arun Munagala (armunaga@iu.edu)
- Shreyas Amit Dhekane (sdhekane@iu.edu)

## Features
- Master-worker architecture with dynamic task scheduling
- Multiple workload partitioning strategies (static vs dynamic)
- FFmpeg-based video processing
- Performance metrics and evaluation tools
- Local simulation and cloud deployment support

## Prerequisites

### Local Development
```bash
# Install FFmpeg
brew install ffmpeg

# Install Python dependencies
pip install -r requirements.txt
```

### Cloud Deployment (Jetstream2)
- Access to Jetstream2 infrastructure
- SSH key configuration
- Shared storage setup (NFS or cloud storage)

## Project Structure
```
├── src/
│   ├── master/          # Master node coordination
│   ├── worker/          # Worker node processing
│   ├── core/            # Core utilities (segmentation, merge, queue)
│   └── evaluation/      # Metrics and performance analysis
├── config/              # Configuration files
├── scripts/             # Deployment and helper scripts
├── tests/               # Unit and integration tests
└── demo/                # Demo videos and examples
```

## Quick Start

### Local Testing
```bash
# Run with dynamic scheduling (default)
python src/main.py --input demo/sample.mp4 --output output/result.mp4 --workers 2

# Run with static partitioning
python src/main.py --input demo/sample.mp4 --output output/result.mp4 --workers 2 --strategy static

# Run single machine baseline
python src/main.py --input demo/sample.mp4 --output output/result.mp4 --workers 1 --strategy single
```

### Cloud Deployment
```bash
# Deploy to Jetstream2
./scripts/deploy.sh

# Run distributed processing
./scripts/run_distributed.sh --input video.mp4 --workers 4
```

## Configuration

Edit `config/config.yaml` to customize:
- Chunk size and duration
- Worker configuration
- Storage paths
- Processing parameters

## Evaluation

```bash
# Run benchmark comparison
python src/evaluation/benchmark.py --input demo/sample.mp4 --workers 1,2,4,8

# Generate performance report
python src/evaluation/report.py --results results/
```

## Architecture

### Master Node
- Accepts input video
- Splits video into segments
- Manages task queue
- Assigns work to workers
- Monitors completion status
- Triggers final merge

### Worker Nodes
- Fetch tasks from queue
- Process video segments with FFmpeg
- Write outputs to shared storage
- Report completion

### Workload Strategies
1. **Single Machine**: Baseline sequential processing
2. **Static Partitioning**: Fixed task assignment per worker
3. **Dynamic Scheduling**: Queue-based task fetching

## License
Academic project - Indiana University Bloomington
