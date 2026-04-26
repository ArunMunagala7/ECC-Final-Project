# Hybrid NFS+SSH Distributed Video Processing

A production-grade distributed video processing framework that combines:
- **Thread-based orchestration** (master-side Python)
- **Real distributed execution** (remote Jetstream2 VMs)
- **Shared storage** (NFS for zero-copy file access)
- **Remote compute** (SSH for FFmpeg execution)

This implementation represents the **best of both worlds** from the previous implementations.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        Master Node                          │
│                                                              │
│  ┌─────────────┐      ┌──────────────────────────┐         │
│  │   Main      │──────▶│  Master Coordinator      │         │
│  │   Entry     │      │  - Segmenter             │         │
│  └─────────────┘      │  - Task Queue            │         │
│                        │  - Thread Pool           │         │
│                        └──────────┬───────────────┘         │
│                                   │                          │
│                        ┌──────────▼───────────┐             │
│                        │  Thread 1│Thread 2│..│             │
│                        │  (Orchestrators)     │             │
│                        └──────────┬───────────┘             │
└───────────────────────────────────┼──────────────────────────┘
                                    │
                          SSH Commands Only
                          (no file transfer)
                                    │
              ┌─────────────────────┼─────────────────────┐
              │                     │                     │
              ▼                     ▼                     ▼
        ┌──────────┐          ┌──────────┐          ┌──────────┐
        │ Worker 1 │          │ Worker 2 │          │ Worker N │
        │          │          │          │          │          │
        │  FFmpeg  │          │  FFmpeg  │          │  FFmpeg  │
        └────┬─────┘          └────┬─────┘          └────┬─────┘
             │                     │                     │
             └─────────────────────┼─────────────────────┘
                                   │
                          ┌────────▼────────┐
                          │   NFS Storage   │
                          │  /nfs_shared/   │
                          │  ├─chunks/      │
                          │  ├─processed/   │
                          │  └─output/      │
                          └─────────────────┘
```

---

## Key Innovations

### 1. **NFS Shared Storage (No File Transfers)**

**Before (SCP):**
```
Master → scp chunk.mp4 → Worker → process → scp result.mp4 → Master
         [SLOW]                            [SLOW]
```

**After (NFS):**
```
Master writes chunk → /nfs_shared/chunks/chunk_000.mp4
Worker reads directly from /nfs_shared/chunks/chunk_000.mp4
Worker writes directly to /nfs_shared/processed/out_000.mp4
Master reads from /nfs_shared/processed/out_000.mp4

No file copying! Just path references.
```

### 2. **SSH for Compute Only**

Workers don't receive files - they receive commands:

```python
# Master sends SSH command:
ssh worker1 "ffmpeg -i /nfs_shared/chunks/chunk_000.mp4 \
                     /nfs_shared/processed/out_000.mp4"

# Worker executes FFmpeg locally, reads/writes to shared NFS
```

### 3. **Thread-Based Orchestration**

Python threads on master coordinate work:

```python
Thread 1: Get chunk_000 → SSH worker1 → Wait for completion
Thread 2: Get chunk_001 → SSH worker2 → Wait for completion
Thread 3: Get chunk_002 → SSH worker1 → Wait for completion
...
```

Threads don't do processing - they just manage remote workers.

---

## Project Structure

```
hybrid-nfs-implementation/
├── src/
│   ├── main.py                 # Entry point
│   ├── core/
│   │   ├── segmenter.py       # Video segmentation
│   │   ├── merger.py          # Video merging
│   │   └── processor.py       # FFmpeg utilities
│   ├── master/
│   │   └── __init__.py        # Master coordinator (static/dynamic)
│   └── worker/
│       └── __init__.py        # RemoteWorker & LocalWorker
├── config/
│   └── config.yaml            # Configuration (workers, NFS paths)
├── scripts/
│   ├── nfs_server_setup.sh    # Setup NFS on master
│   ├── nfs_client_setup.sh    # Mount NFS on workers
│   ├── deploy.sh              # Deploy code to Jetstream
│   └── test_local.sh          # Local testing without cloud
├── JETSTREAM_SETUP.md         # Complete Jetstream guide
├── README.md                  # This file
└── TESTING.md                 # Testing instructions
```

---

## Quick Start

### Local Testing (No Cloud Required)

```bash
# 1. Install FFmpeg
brew install ffmpeg  # macOS
# sudo apt-get install -y ffmpeg  # Linux

# 2. Install Python dependencies
pip3 install pyyaml

# 3. Run local test
cd hybrid-nfs-implementation
chmod +x scripts/test_local.sh
./scripts/test_local.sh
```

This uses `LocalWorker` to simulate distributed processing on your machine.

### Jetstream2 Deployment

**Full setup guide:** See [JETSTREAM_SETUP.md](JETSTREAM_SETUP.md)

**Quick summary:**
1. Create Jetstream2 VMs (1 master + 4 workers)
2. Setup NFS server on master: `sudo bash scripts/nfs_server_setup.sh`
3. Mount NFS on workers: `sudo bash scripts/nfs_client_setup.sh <master_ip>`
4. Deploy code: `./scripts/deploy.sh`
5. Update `config/config.yaml` with worker IPs
6. Run: `python3 src/main.py --input video.mp4 --strategy dynamic --remote`

---

## Usage

### Basic Command

```bash
python3 src/main.py --input video.mp4 --strategy dynamic --remote
```

### Options

```
--input PATH          Input video file (required)
--strategy STRATEGY   Scheduling strategy: static or dynamic (default: dynamic)
--config PATH         Config file path (default: config/config.yaml)
--remote              Use remote Jetstream workers (default: local simulation)
```

### Examples

**Local testing (static):**
```bash
python3 src/main.py --input test.mp4 --strategy static
```

**Local testing (dynamic):**
```bash
python3 src/main.py --input test.mp4 --strategy dynamic
```

**Jetstream deployment (static):**
```bash
python3 src/main.py --input video.mp4 --strategy static --remote
```

**Jetstream deployment (dynamic):**
```bash
python3 src/main.py --input video.mp4 --strategy dynamic --remote
```

---

## Scheduling Strategies

### Static Scheduling

**How it works:**
- Fixed assignment: Chunk `i` goes to Worker `(i % num_workers)`
- Chunk 0 → Worker 0
- Chunk 1 → Worker 1
- Chunk 2 → Worker 2
- Chunk 3 → Worker 3
- Chunk 4 → Worker 0 (wraps around)

**Pros:**
- Simple, predictable
- Even distribution
- Low coordination overhead

**Cons:**
- Load imbalance if chunks vary in complexity
- No adaptation to worker speed differences

### Dynamic Scheduling

**How it works:**
- Shared task queue with all chunks
- Workers pull next task when idle
- Automatic load balancing
- Retry failed tasks on different workers

**Pros:**
- Handles worker heterogeneity
- Fault tolerance through retries
- Better load balance

**Cons:**
- Slightly more coordination overhead
- More complex implementation

---

## Configuration

Edit `config/config.yaml`:

```yaml
# NFS configuration
nfs_base_dir: "/home/ubuntu/nfs_shared"

# SSH configuration
ssh_user: "ubuntu"
ssh_key: "~/.ssh/jetstream_key"

# Worker nodes (update with your IPs)
workers:
  - host: "worker1.jetstream.org"
  - host: "worker2.jetstream.org"
  - host: "worker3.jetstream.org"
  - host: "worker4.jetstream.org"

# Processing settings
segment_duration: 5     # seconds
codec: "libx264"
bitrate: "2M"
preset: "medium"        # ultrafast, fast, medium, slow
max_retries: 2          # for dynamic scheduling
```

---

## How It Differs From Previous Implementations

### vs. Main Implementation (`src/`)

| Feature | Main Implementation | Hybrid NFS+SSH |
|---------|-------------------|----------------|
| **Workers** | Python threads (simulated) | Real VMs (actual distributed) |
| **Storage** | Local filesystem | NFS shared storage |
| **Execution** | Local FFmpeg calls | Remote SSH FFmpeg |
| **Deployment** | Single machine | Multi-node cluster |
| **Scalability** | Limited by CPU cores | Limited by VMs available |

### vs. SSH/SCP Implementation (`distributed-ssh-implementation/`)

| Feature | SSH/SCP Implementation | Hybrid NFS+SSH |
|---------|----------------------|----------------|
| **File Transfer** | SCP before & after | None (shared NFS) |
| **Framework** | Minimal/custom | Modular/structured |
| **Configuration** | Hardcoded | YAML config |
| **Worker Management** | Basic | Thread pool orchestration |
| **Fault Tolerance** | Limited | Retry mechanism |
| **Performance** | Slower (2x transfer) | Faster (zero copy) |

---

## Performance Expectations

### With NFS vs. SCP

**For a 100MB video segment:**

```
SCP Method:
  Copy to worker:   5 seconds
  Process:          10 seconds
  Copy back:        5 seconds
  Total:            20 seconds

NFS Method:
  Copy to worker:   0 seconds (already visible)
  Process:          10 seconds
  Copy back:        0 seconds (writes directly to shared storage)
  Total:            10 seconds

Speedup: 2x
```

### Scalability

**Expected speedup with 4 workers:**
- **Single machine:** 60 seconds
- **Static (4 workers):** ~18 seconds (3.3x speedup)
- **Dynamic (4 workers):** ~16 seconds (3.75x speedup)

Accounts for:
- Segmentation overhead
- Merging overhead
- Network latency
- Load imbalance

---

## Testing

See [TESTING.md](TESTING.md) for comprehensive testing guide.

**Quick tests:**

```bash
# Local simulation
./scripts/test_local.sh

# Jetstream static
python3 src/main.py --input test.mp4 --strategy static --remote

# Jetstream dynamic
python3 src/main.py --input test.mp4 --strategy dynamic --remote
```

---

## Troubleshooting

### "FFmpeg not found"
```bash
# macOS
brew install ffmpeg

# Ubuntu (on Jetstream VMs)
sudo apt-get install -y ffmpeg
```

### "NFS mount failed"
```bash
# On master, check NFS is running
sudo systemctl status nfs-kernel-server
showmount -e localhost

# On worker, remount
sudo umount /home/ubuntu/nfs_shared
sudo mount <master_ip>:/home/ubuntu/nfs_shared /home/ubuntu/nfs_shared
```

### "SSH connection refused"
```bash
# Check SSH key permissions
chmod 600 ~/.ssh/jetstream_key

# Test connection
ssh -v -i ~/.ssh/jetstream_key ubuntu@<worker_ip>

# Verify IPs in config/config.yaml match actual VMs
```

### "Permission denied" on NFS
```bash
# On master, fix permissions
sudo chown -R ubuntu:ubuntu /home/ubuntu/nfs_shared
sudo chmod -R 755 /home/ubuntu/nfs_shared
```

---

## Dependencies

**Python:**
- Python 3.8+
- pyyaml

**System:**
- FFmpeg
- NFS server (master)
- NFS client (workers)
- SSH

**Cloud (optional):**
- Jetstream2 account (or any cloud with Ubuntu VMs)

---

## Advantages of This Architecture

✅ **Zero file transfer overhead** - NFS shared storage  
✅ **Real distributed execution** - Actual VMs, not simulation  
✅ **Clean separation** - Orchestration vs. compute  
✅ **Fault tolerance** - Retry mechanism for failed tasks  
✅ **Flexible** - Works locally for testing, remotely for production  
✅ **Scalable** - Add more workers by updating config  
✅ **Maintainable** - Modular, well-structured code  
✅ **Production-ready** - Similar to real distributed systems  

---

## Future Enhancements

- **GPU acceleration** - Use FFmpeg with NVENC on GPU-enabled VMs
- **Adaptive scheduling** - Profile worker speed and adjust assignments
- **Container deployment** - Docker/Kubernetes for easier deployment
- **Monitoring dashboard** - Real-time progress visualization
- **Auto-scaling** - Dynamically add/remove workers based on load
- **Checkpoint/resume** - Save state for long-running jobs

---

## Credits

This implementation combines insights from:
- Main thread-based framework (`src/`)
- SSH/SCP distributed approach (`distributed-ssh-implementation/`)
- Industry best practices (Hadoop, Spark, Dask architectures)

---

## License

MIT License - See project root for details

---

## Support

- **Jetstream Setup:** See [JETSTREAM_SETUP.md](JETSTREAM_SETUP.md)
- **Testing Guide:** See [TESTING.md](TESTING.md)
- **Configuration:** See `config/config.yaml`

---

**Ready to process videos at scale! 🚀🎬**
