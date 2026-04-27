# Hybrid NFS+SSH Distributed Video Processing System

## Project Overview

A distributed video processing system that combines Python threading orchestration with real cloud infrastructure execution. The system uses NFS shared storage and SSH remote execution to process video chunks in parallel across multiple Jetstream2 cloud VMs.

## Architecture

### Components
- **Master Node**: Orchestrates processing, segments videos, and merges results
- **Worker Nodes**: Execute FFmpeg processing commands on assigned chunks
- **NFS Shared Storage**: Network file system mounted on all nodes for zero-copy file sharing
- **SSH**: Remote command execution from master to workers

### Technology Stack
- **Language**: Python 3
- **Video Processing**: FFmpeg
- **Concurrency**: ThreadPoolExecutor (Python threading)
- **Storage**: NFS (Network File System)
- **Remote Execution**: SSH (key-based authentication)
- **Cloud Platform**: Jetstream2 via Exosphere

## Implementation Steps

### 1. Local Development & Testing

#### Created Project Structure
```bash
hybrid-nfs-implementation/
├── src/
│   ├── main.py              # Entry point with --remote flag
│   ├── core/
│   │   ├── segmenter.py     # Video segmentation
│   │   ├── processor.py     # FFmpeg command builder
│   │   └── merger.py        # Segment merging
│   ├── master/
│   │   └── __init__.py      # Static & dynamic scheduling
│   └── worker/
│       └── __init__.py      # RemoteWorker & LocalWorker
├── config/
│   └── config.yaml          # Worker IPs and paths
└── scripts/                 # Setup and deployment scripts
```

#### Local Testing Results
```bash
# Dynamic Scheduling
python3 src/main.py --input test_videos/test_input.mp4 --strategy dynamic
Total time: 0.79s
Success rate: 100% (3/3 chunks)

# Static Scheduling
python3 src/main.py --input test_videos/test_input.mp4 --strategy static
Total time: 0.94s
Success rate: 100% (3/3 chunks)

# Performance: Dynamic is 16% faster than static
```

#### Git Repository
```bash
git add .
git commit -m "Add hybrid NFS+SSH implementation"
git push origin main
# Commit: 8aeb026
```

### 2. Jetstream2 Cloud Deployment

#### VM Configuration
```
Master VM:
- Instance: m3.medium
- IP: 149.165.170.232
- OS: Ubuntu 22.04
- User: exouser

Worker VMs (4 nodes):
- Worker 1: 149.165.169.199
- Worker 2: 149.165.169.58
- Worker 3: 149.165.169.92
- Worker 4: 149.165.172.111
- Instance Type: m3.medium
- OS: Ubuntu 22.04
- User: exouser
```

#### NFS Server Setup (Master Node)
```bash
# Install NFS server
sudo apt update
sudo apt install -y nfs-kernel-server

# Create shared directory
sudo mkdir -p /home/ubuntu/nfs_shared
sudo chown -R exouser:exouser /home/ubuntu/nfs_shared
sudo chmod 777 /home/ubuntu/nfs_shared

# Configure NFS exports
echo "/home/ubuntu/nfs_shared *(rw,sync,no_subtree_check,no_root_squash)" | sudo tee -a /etc/exports

# Apply configuration
sudo exportfs -ra
sudo systemctl restart nfs-kernel-server

# Verify NFS is running
sudo systemctl status nfs-kernel-server
```

#### NFS Client Setup (All Worker Nodes)
```bash
# Install NFS client (on each worker)
sudo apt update
sudo apt install -y nfs-common

# Create mount point
sudo mkdir -p /home/ubuntu/nfs_shared

# Mount NFS share
sudo mount 149.165.170.232:/home/ubuntu/nfs_shared /home/ubuntu/nfs_shared

# Verify mount
df -h | grep nfs_shared
# Output: 149.165.170.232:/home/ubuntu/nfs_shared   49G  5.2G   41G  12% /home/ubuntu/nfs_shared

# Make mount persistent (add to /etc/fstab)
echo "149.165.170.232:/home/ubuntu/nfs_shared /home/ubuntu/nfs_shared nfs defaults 0 0" | sudo tee -a /etc/fstab
```

#### FFmpeg Installation (All Nodes)
```bash
# Install FFmpeg on master and all workers
sudo apt update
sudo apt install -y ffmpeg

# Verify installation
ffmpeg -version
# Output: ffmpeg version 4.4.2-0ubuntu0.22.04.1
```

#### Code Deployment (Master Node)
```bash
# From local Mac
scp -r hybrid-nfs-implementation/src exouser@149.165.170.232:~/video_processing/
scp -r hybrid-nfs-implementation/config exouser@149.165.170.232:~/video_processing/

# Verify deployment
ssh exouser@149.165.170.232
ls -la ~/video_processing/
# Output: src/ config/
```

#### Test Video Creation
```bash
# On master node
ffmpeg -f lavfi -i testsrc=duration=30:size=1280x720:rate=30 \
       -pix_fmt yuv420p /home/ubuntu/nfs_shared/test_input.mp4

# Verify video
ls -lh /home/ubuntu/nfs_shared/test_input.mp4
# Output: -rw-rw-r-- 1 exouser exouser 855K Apr 27 05:30 test_input.mp4

ffprobe /home/ubuntu/nfs_shared/test_input.mp4
# Duration: 00:00:30.00, 1280x720, 30 fps
```

### 3. SSH Key-Based Authentication Setup

#### Generate SSH Key (Master Node)
```bash
ssh-keygen -t rsa -b 2048 -f ~/.ssh/id_rsa -N ""
# Output:
# Your identification has been saved in /home/exouser/.ssh/id_rsa
# Your public key has been saved in /home/exouser/.ssh/id_rsa.pub

# Display public key
cat ~/.ssh/id_rsa.pub
# Output: ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCuAx/skhaTpnGUysR6rI1gKpJrEEJQCubCgzQXFXtTnBvMFG3WYDkE8/eQTEuQ4Pn57TFO70cwN9SWttRry8ML3Dvnt5mZZznIVUY0nsPKeP3ZIrxO0HPjxTD4lVJy4NUn6CWneBd7ixyxaRssouot2E57S/hJSS/fCdCnCzi7di61pQTyeucheicNAFxYwpES50M0w2/niXLBtVNn8/nKqgRxPz3YIm4lwG6iW/tog2lZh77Mmhw97X93v5qrq0TepXABJ1g1A5OIlz558vOorP/upIMd5aEeAQq6Ajbq2RHmz8H5NEjBSz5GNKoPdKWIkEutOIBWZs4EpXo0Fa3d exouser@video-master
```

#### Add Master's Key to Workers
```bash
# On each worker (from local Mac)
ssh exouser@149.165.169.199
echo "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCuAx/skhaTpnGUysR6rI1gKpJrEEJQCubCgzQXFXtTnBvMFG3WYDkE8/eQTEuQ4Pn57TFO70cwN9SWttRry8ML3Dvnt5mZZznIVUY0nsPKeP3ZIrxO0HPjxTD4lVJy4NUn6CWneBd7ixyxaRssouot2E57S/hJSS/fCdCnCzi7di61pQTyeucheicNAFxYwpES50M0w2/niXLBtVNn8/nKqgRxPz3YIm4lwG6iW/tog2lZh77Mmhw97X93v5qrq0TepXABJ1g1A5OIlz558vOorP/upIMd5aEeAQq6Ajbq2RHmz8H5NEjBSz5GNKoPdKWIkEutOIBWZs4EpXo0Fa3d exouser@video-master" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
exit

# Repeat for workers: 149.165.169.58, 149.165.169.92, 149.165.172.111
```

#### Test Passwordless SSH
```bash
# From master node
ssh exouser@149.165.169.199 'echo "Worker 1 OK"'
ssh exouser@149.165.169.58 'echo "Worker 2 OK"'
ssh exouser@149.165.169.92 'echo "Worker 3 OK"'
ssh exouser@149.165.172.111 'echo "Worker 4 OK"'
# All connections successful without password prompts
```

### 4. Distributed Processing Execution

#### Dynamic Scheduling Test
```bash
python3 src/main.py --input /home/ubuntu/nfs_shared/test_input.mp4 \
                    --strategy dynamic \
                    --config config/config.yaml \
                    --remote
```

**Output:**
```
✓ FFmpeg found
✓ Loaded config from /home/exouser/video_processing/config/config.yaml
✓ Input video: /home/ubuntu/nfs_shared/test_input.mp4

============================================================
Mode: REMOTE (Jetstream)
Strategy: DYNAMIC
============================================================

Created RemoteWorker 0: 149.165.169.199
Created RemoteWorker 1: 149.165.169.58
Created RemoteWorker 2: 149.165.169.92
Created RemoteWorker 3: 149.165.172.111
✓ Created 4 workers

Segmenting video into /home/ubuntu/nfs_shared/chunks...
Created segment 1/6: chunk_000.mp4
Created segment 2/6: chunk_001.mp4
Created segment 3/6: chunk_002.mp4
Created segment 4/6: chunk_003.mp4
Created segment 5/6: chunk_004.mp4
Created segment 6/6: chunk_005.mp4
Created 6 segments

Processing 6 chunks dynamically...
  ✓ Chunk 0 completed by Worker 0 (1.28s)
  ✓ Chunk 1 completed by Worker 1 (1.35s)
  ✓ Chunk 3 completed by Worker 3 (1.61s)
  ✓ Chunk 2 completed by Worker 2 (1.64s)
  ✓ Chunk 4 completed by Worker 0 (1.19s)
  ✓ Chunk 5 completed by Worker 1 (1.28s)

Merging processed segments...
Merged 6 segments into /home/ubuntu/nfs_shared/output/final_dynamic.mp4

=== Dynamic Processing Complete ===
Total time: 6.03s
Successful: 6/6
Output: /home/ubuntu/nfs_shared/output/final_dynamic.mp4

Worker Statistics:
  Worker 0 (149.165.169.199): 2 completed, 0 failed
  Worker 1 (149.165.169.58): 2 completed, 0 failed
  Worker 2 (149.165.169.92): 1 completed, 0 failed
  Worker 3 (149.165.172.111): 1 completed, 0 failed
```

#### Static Scheduling Test
```bash
python3 src/main.py --input /home/ubuntu/nfs_shared/test_input.mp4 \
                    --strategy static \
                    --config config/config.yaml \
                    --remote
```

**Output:**
```
============================================================
Mode: REMOTE (Jetstream)
Strategy: STATIC
============================================================

Created RemoteWorker 0: 149.165.169.199
Created RemoteWorker 1: 149.165.169.58
Created RemoteWorker 2: 149.165.169.92
Created RemoteWorker 3: 149.165.172.111
✓ Created 4 workers

Segmenting video into /home/ubuntu/nfs_shared/chunks...
Created 6 segments

Assigning chunks to workers (static round-robin)...
  Chunk 0 → Worker 0
  Chunk 1 → Worker 1
  Chunk 2 → Worker 2
  Chunk 3 → Worker 3
  Chunk 4 → Worker 0
  Chunk 5 → Worker 1

Processing 6 chunks...
  [1/6] ✓ Chunk 0 (Worker 0, 1.47s)
  [2/6] ✓ Chunk 1 (Worker 1, 1.56s)
  [3/6] ✓ Chunk 2 (Worker 2, 1.70s)
  [4/6] ✓ Chunk 3 (Worker 3, 1.72s)
  [5/6] ✓ Chunk 4 (Worker 0, 1.18s)
  [6/6] ✓ Chunk 5 (Worker 1, 1.28s)

Merging processed segments...
Merged 6 segments into /home/ubuntu/nfs_shared/output/final_static.mp4

=== Static Processing Complete ===
Total time: 6.08s
Successful: 6/6
Output: /home/ubuntu/nfs_shared/output/final_static.mp4

Worker Statistics:
  Worker 0 (149.165.169.199): 2 completed, 0 failed
  Worker 1 (149.165.169.58): 2 completed, 0 failed
  Worker 2 (149.165.169.92): 1 completed, 0 failed
  Worker 3 (149.165.172.111): 1 completed, 0 failed
```

#### Output Video Verification
```bash
ls -lh /home/ubuntu/nfs_shared/output/
# Output:
# -rw-rw-r-- 1 exouser exouser 4.2M Apr 27 05:44 final_dynamic.mp4
# -rw-rw-r-- 1 exouser exouser 4.2M Apr 27 05:45 final_static.mp4

ffprobe /home/ubuntu/nfs_shared/output/final_dynamic.mp4
# Output:
# Duration: 00:00:30.00, bitrate: 1165 kb/s
# Video: h264 (High), yuv420p, 1280x720 [SAR 1:1 DAR 16:9], 30 fps
```

## Performance Results

### Local Testing (Mac)
| Strategy | Time | Success Rate | Performance |
|----------|------|--------------|-------------|
| Dynamic  | 0.79s | 100% (3/3) | **Baseline** |
| Static   | 0.94s | 100% (3/3) | 16% slower |

**Dynamic scheduling is 16% faster** due to load balancing.

### Distributed Testing (Jetstream2 - 4 Workers)
| Strategy | Time | Success Rate | Workers Used | Performance |
|----------|------|--------------|--------------|-------------|
| Dynamic  | 6.03s | 100% (6/6) | All 4 workers | **Baseline** |
| Static   | 6.08s | 100% (6/6) | All 4 workers | 0.83% slower |

**Minimal difference** on cloud due to similar chunk processing times and network overhead.

### Key Observations

1. **Scalability**: Successfully distributed 6 chunks across 4 cloud VMs
2. **Reliability**: 100% success rate on both local and distributed execution
3. **Load Balancing**: Dynamic scheduling automatically balanced work:
   - Workers 0 & 1: 2 chunks each
   - Workers 2 & 3: 1 chunk each
4. **Network Efficiency**: NFS shared storage eliminated file transfer overhead
5. **Processing Time**: Individual chunks took 1.2-1.7 seconds on cloud VMs

## Configuration

### config.yaml
```yaml
workers:
  - ip: "149.165.169.199"
  - ip: "149.165.169.58"
  - ip: "149.165.169.92"
  - ip: "149.165.172.111"

ssh_user: "exouser"
nfs_base_dir: "/home/ubuntu/nfs_shared"

processing:
  segment_duration: 5
  output_format: "mp4"
  video_codec: "libx264"
  audio_codec: "aac"
```

## Key Technical Decisions

### 1. NFS vs SCP File Transfer
**Decision**: Use NFS shared storage  
**Rationale**: 
- Zero-copy architecture (no file transfers needed)
- All nodes access same storage directly
- Reduced network overhead
- Simplified error handling

### 2. SSH Remote Execution
**Decision**: Use subprocess SSH commands  
**Rationale**:
- Simple and reliable
- Standard Linux tool
- No additional Python libraries needed
- Easy to debug

### 3. ThreadPoolExecutor for Concurrency
**Decision**: Python threading instead of multiprocessing  
**Rationale**:
- SSH/network operations are I/O-bound (GIL not an issue)
- Simpler state sharing
- Lower overhead than multiprocessing

### 4. FFmpeg Re-encoding During Segmentation
**Decision**: Use `-c:v libx264` instead of `-c copy`  
**Rationale**:
- Precise segment timing
- Avoids corrupted chunks
- Ensures clean merging

## Troubleshooting & Solutions

### Issue 1: Permission Denied on NFS Directory
**Error**: `Permission denied: '/home/ubuntu/nfs_shared/chunks'`  
**Solution**: 
```bash
sudo chown -R exouser:exouser /home/ubuntu/nfs_shared
sudo chmod 777 /home/ubuntu/nfs_shared
```

### Issue 2: SSH Password Prompts
**Error**: `exouser@149.165.169.199's password:`  
**Solution**: Set up SSH key-based authentication
```bash
ssh-keygen -t rsa -b 2048 -f ~/.ssh/id_rsa -N ""
# Add master's public key to each worker's ~/.ssh/authorized_keys
```

### Issue 3: Corrupted Last Segment
**Error**: Last chunk was 262 bytes (corrupted)  
**Solution**: Fixed segment calculation
```python
# Before: num_segments = math.ceil(duration / segment_duration) + 1
# After: num_segments = math.ceil(duration / segment_duration)
```

## System Requirements

### Master Node
- Python 3.8+
- FFmpeg 4.4+
- NFS server
- SSH client
- 2+ CPU cores
- 4+ GB RAM

### Worker Nodes
- FFmpeg 4.4+
- NFS client
- SSH server
- 2+ CPU cores
- 4+ GB RAM

### Network
- Low-latency connection between master and workers
- NFS port 2049 open
- SSH port 22 open

## Future Enhancements

1. **Fault Tolerance**: Retry failed chunks automatically
2. **Load Monitoring**: Track worker CPU/memory usage
3. **Adaptive Scheduling**: Adjust chunk size based on worker performance
4. **Web Dashboard**: Real-time monitoring UI
5. **Container Deployment**: Docker/Kubernetes for easier setup
6. **Larger Scale Testing**: 10+ workers with longer videos
7. **GPU Acceleration**: Use FFmpeg with NVENC for faster encoding

## Conclusion

Successfully implemented and deployed a hybrid distributed video processing system that:
- ✅ Combines Python threading with real cloud infrastructure
- ✅ Uses NFS shared storage for efficient file access
- ✅ Executes SSH remote commands for distributed processing
- ✅ Achieves 100% success rate on both local and cloud environments
- ✅ Demonstrates both static and dynamic scheduling strategies
- ✅ Scales across multiple Jetstream2 cloud VMs

The system proves the viability of NFS+SSH architecture for distributed video processing workloads on cloud infrastructure.

## Repository

GitHub: https://github.com/ArunMunagala7/ECC-Final-Project  
Branch: main  
Commit: 8aeb026

## Author

Arun Munagala  
Date: April 27, 2026
