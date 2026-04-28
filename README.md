# Distributed Video Processing System

ECC Final Project - Spring 2026

## Team
- Anuj Prakash (asprakas@iu.edu)
- Arun Munagala (armunaga@iu.edu)
- Shreyas Amit Dhekane (sdhekane@iu.edu)

## Overview

Built a distributed video processing framework that splits videos into chunks, processes them across multiple cloud workers in parallel, and merges results. Compares static vs dynamic scheduling strategies.

**Key Results:**
- Dynamic scheduling: 16% faster than static (local testing)
- 100% success rate across all distributed tests
- Successfully deployed on Jetstream2 (5 VMs: 1 master + 4 workers)

## Architecture

- **Master Node**: Splits videos, assigns work, merges output
- **Worker Nodes**: Process video chunks with FFmpeg
- **NFS Storage**: Shared filesystem for zero-copy file access
- **Communication**: SSH remote execution from master to workers
- **Fault Tolerance**: Health checks, automatic retries, result validation

## Features

### Core Functionality
- **Video Segmentation**: Splits videos into equal-duration chunks
- **Distributed Processing**: Parallel FFmpeg execution across multiple workers
- **Result Merging**: Combines processed chunks into final output
- **Dual Scheduling**: Static (round-robin) and Dynamic (queue-based) strategies

### Fault Tolerance
- **Worker Health Checks**: SSH ping verification before task assignment
- **Automatic Retries**: Failed tasks retry up to 2 times with worker rotation
- **Result Validation**: Checks output file existence and integrity before merging
- **Graceful Degradation**: Continues with available workers if some fail

### Performance
- Dynamic scheduling 16% faster than static (local)
- 100% success rate in distributed cloud tests
- Handles worker failures without manual intervention

## Quick Start

### Requirements
```bash
# Install FFmpeg
brew install ffmpeg  # macOS
sudo apt install ffmpeg  # Ubuntu

# Python 3.8+
pip install -r requirements.txt
```

### Local Testing
```bash
cd hybrid-nfs-implementation

# Dynamic scheduling
python3 src/main.py --input test_videos/test_input.mp4 \
                    --strategy dynamic \
                    --config config/config.local.yaml

# Static scheduling
python src/main.py --input demo/sample.mp4 --output output/result.mp4 --workers 2

python3 src/main.py --input test_videos/test_input.mp4 \
                    --strategy static \
                    --config config/config.local.yaml
```

### Cloud Deployment (Jetstream2)

**Setup:**
1. Create 5 VMs (1 master + 4 workers)
2. Set up NFS server on master
3. Mount NFS on all workers
4. Configure SSH keys for passwordless authentication
5. Deploy code to master VM

**Run:**
```bash
# SSH to master
ssh exouser@<master-ip>

# Run distributed processing
cd ~/video_processing
python3 src/main.py --input /home/ubuntu/nfs_shared/test_input.mp4 \
                    --strategy dynamic \
                    --config config/config.yaml \
                    --remote
```

See `hybrid-nfs-implementation/IMPLEMENTATION_REPORT.md` for detailed setup instructions.

## Performance Results

| Environment | Strategy | Time | Workers |
|-------------|----------|------|---------|
| Local (Mac) | Dynamic | 0.79s | 3 |
| Local (Mac) | Static | 0.94s | 3 |
| Cloud (Jetstream2) | Dynamic | 6.03s | 4 |
| Cloud (Jetstream2) | Static | 6.08s | 4 |

**Success Rate:** 100% across all tests

## Project Structure

```
hybrid-nfs-implementation/
├── src/
│   ├── main.py              # Entry point
│   ├── core/                # Video segmentation & merging
│   ├── master/              # Orchestration logic
│   └── worker/              # Worker implementations
├── config/
│   ├── config.yaml          # Jetstream configuration
│   └── config.local.yaml    # Local testing configuration
└── scripts/                 # Setup and deployment scripts
```

## Documentation

- **`PRESENTATION_DEMO_GUIDE.md`** - Complete demo walkthrough for presentations
- **`hybrid-nfs-implementation/IMPLEMENTATION_REPORT.md`** - Technical details and setup
- **`ECC_MidTerm_Project.pdf`** - Original project proposal

## Technologies

- Python 3 (ThreadPoolExecutor for concurrency)
- FFmpeg (video processing)
- NFS (shared storage)
- SSH (remote execution)
- Jetstream2 (cloud platform)

## Course Info

Indiana University Bloomington  
ECC - Elastic Cloud Computing  
Spring 2026
