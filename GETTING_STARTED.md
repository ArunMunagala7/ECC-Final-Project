# Getting Started Guide

## Quick Setup (Local Development)

### 1. Install FFmpeg

FFmpeg is required for video processing:

```bash
brew install ffmpeg
```

Verify installation:
```bash
ffmpeg -version
```

### 2. Install Python Dependencies

```bash
cd /Users/arunmunagala/ECC_FInal_Project
pip3 install -r requirements.txt
```

### 3. Run Demo

The easiest way to test the system locally:

```bash
./scripts/demo.sh
```

This will:
- Create a test video
- Run single-machine processing
- Run static partitioning (2 workers)
- Run dynamic scheduling (2 workers)
- Compare results

### 4. Run with Your Own Video

```bash
# Dynamic scheduling (recommended)
python3 src/main.py --input path/to/video.mp4 --output output/result.mp4 --workers 4

# Static partitioning
python3 src/main.py --input path/to/video.mp4 --output output/result.mp4 --workers 4 --strategy static

# Single machine baseline
python3 src/main.py --input path/to/video.mp4 --output output/result.mp4 --strategy single
```

### 5. Run Benchmark

Compare all strategies:

```bash
python3 src/evaluation/benchmark.py --input demo/sample.mp4 --workers 1,2,4,8
```

## Cloud Deployment (Jetstream2)

### Prerequisites

1. **Jetstream2 Account**: Get access at [https://jetstream-cloud.org/](https://jetstream-cloud.org/)
2. **SSH Key**: Generate and configure SSH keys for your instances
3. **VM Instances**: Create at least 2 instances (1 master, 1+ workers)
4. **Shared Storage**: Setup NFS or cloud storage accessible to all nodes

### Setup Steps

#### 1. Configure Hosts

Edit your local `~/.ssh/config`:

```
Host jetstream-master
    HostName <master-ip>
    User ubuntu
    IdentityFile ~/.ssh/jetstream2_key

Host jetstream-worker-1
    HostName <worker1-ip>
    User ubuntu
    IdentityFile ~/.ssh/jetstream2_key

Host jetstream-worker-2
    HostName <worker2-ip>
    User ubuntu
    IdentityFile ~/.ssh/jetstream2_key
```

#### 2. Setup Shared Storage (NFS)

On master node:
```bash
# Install NFS server
sudo apt-get update
sudo apt-get install -y nfs-kernel-server

# Create shared directory
sudo mkdir -p /shared/video-storage
sudo chown ubuntu:ubuntu /shared/video-storage

# Configure NFS export
echo "/shared/video-storage *(rw,sync,no_subtree_check,no_root_squash)" | sudo tee -a /etc/exports
sudo exportfs -a
sudo systemctl restart nfs-kernel-server
```

On worker nodes:
```bash
# Install NFS client
sudo apt-get update
sudo apt-get install -y nfs-common

# Mount shared storage
sudo mkdir -p /shared/video-storage
sudo mount <master-ip>:/shared/video-storage /shared/video-storage

# Make mount persistent
echo "<master-ip>:/shared/video-storage /shared/video-storage nfs defaults 0 0" | sudo tee -a /etc/fstab
```

#### 3. Update Configuration

Edit `config/config.yaml`:

```yaml
storage:
  mode: remote
  base_path: /shared/video-storage
  # ... rest of config
```

#### 4. Deploy Code

```bash
export MASTER_HOST=jetstream-master
export WORKER_HOSTS="jetstream-worker-1 jetstream-worker-2"
export SSH_KEY=~/.ssh/jetstream2_key

./scripts/deploy.sh
```

#### 5. Run Distributed Processing

```bash
./scripts/run_distributed.sh --input my_video.mp4 --workers 4 --strategy dynamic
```

## Architecture Overview

```
┌─────────────────────────────────────────────────┐
│                  Master Node                    │
│  ┌──────────────────────────────────────────┐  │
│  │  Video Segmenter                         │  │
│  │  Task Queue Manager                      │  │
│  │  Worker Coordinator                      │  │
│  │  Video Merger                            │  │
│  └──────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
                     │
        ┌────────────┼────────────┐
        │            │            │
    ┌───▼───┐    ┌───▼───┐    ┌───▼───┐
    │Worker │    │Worker │    │Worker │
    │   1   │    │   2   │    │   N   │
    └───┬───┘    └───┬───┘    └───┬───┘
        │            │            │
        └────────────┼────────────┘
                     │
        ┌────────────▼────────────┐
        │   Shared Storage (NFS)  │
        │  - Input videos         │
        │  - Video chunks         │
        │  - Processed segments   │
        │  - Final output         │
        └─────────────────────────┘
```

## Troubleshooting

### FFmpeg Not Found
```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt-get install -y ffmpeg
```

### Import Errors
```bash
pip3 install -r requirements.txt
```

### Permission Denied on Scripts
```bash
chmod +x scripts/*.sh
```

### NFS Mount Issues

Check NFS is running:
```bash
# On master
sudo systemctl status nfs-kernel-server

# On workers
sudo mount | grep nfs
```

Remount if needed:
```bash
sudo umount /shared/video-storage
sudo mount <master-ip>:/shared/video-storage /shared/video-storage
```

## What You Need to Do

✅ **Done in VS Code:**
- Complete Python implementation
- Configuration files
- Local testing scripts
- Deployment scripts

⚠️ **You Need to Do:**

1. **Install FFmpeg** (1 minute):
   ```bash
   brew install ffmpeg
   ```

2. **Install Python packages** (2 minutes):
   ```bash
   pip3 install -r requirements.txt
   ```

3. **Test locally** (5 minutes):
   ```bash
   ./scripts/demo.sh
   ```

4. **For cloud deployment** (optional, 30-60 minutes):
   - Create Jetstream2 VMs
   - Setup SSH keys
   - Configure NFS shared storage
   - Run deployment script
   - Test distributed processing

## Next Steps

1. **Local Testing**: Run `./scripts/demo.sh` to verify everything works
2. **Custom Videos**: Test with your own videos
3. **Benchmarking**: Run comprehensive benchmarks
4. **Cloud Deployment**: Deploy to Jetstream2 for real distributed testing
5. **Documentation**: The implementation matches the PDF requirements!

## Support

If you encounter issues:
1. Check logs in `logs/` directory
2. Review metrics in `metrics/` directory
3. Verify FFmpeg is installed: `ffmpeg -version`
4. Check Python imports: `python3 -c "import yaml; print('OK')"`
