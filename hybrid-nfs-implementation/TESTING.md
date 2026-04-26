# Testing Guide

Comprehensive testing instructions for the hybrid NFS+SSH implementation.

---

## Table of Contents

1. [Local Testing](#local-testing)
2. [Jetstream Testing](#jetstream-testing)
3. [Performance Benchmarking](#performance-benchmarking)
4. [Validation](#validation)
5. [Comparison Testing](#comparison-testing)

---

## Local Testing

Test the framework **without Jetstream** using simulated local workers.

### Prerequisites

```bash
# Install FFmpeg
brew install ffmpeg  # macOS
sudo apt-get install -y ffmpeg  # Linux

# Install Python dependencies
pip3 install pyyaml

# Verify installation
ffmpeg -version
python3 --version
```

### Quick Test Script

```bash
cd hybrid-nfs-implementation
chmod +x scripts/test_local.sh
./scripts/test_local.sh
```

This script:
1. Creates a test video
2. Runs static scheduling
3. Runs dynamic scheduling
4. Shows results

### Manual Testing

**Create test video:**
```bash
mkdir -p test_videos
ffmpeg -f lavfi -i testsrc=duration=30:size=1280x720:rate=30 \
       -pix_fmt yuv420p -c:v libx264 -y test_videos/test_30s.mp4
```

**Test static scheduling:**
```bash
python3 src/main.py \
    --input test_videos/test_30s.mp4 \
    --strategy static \
    --config config/config.yaml
```

**Test dynamic scheduling:**
```bash
python3 src/main.py \
    --input test_videos/test_30s.mp4 \
    --strategy dynamic \
    --config config/config.yaml
```

**Check outputs:**
```bash
ls -lh /tmp/video_processing/output/
# Should see: final_static.mp4 and final_dynamic.mp4

# Play output
open /tmp/video_processing/output/final_dynamic.mp4  # macOS
vlc /tmp/video_processing/output/final_dynamic.mp4   # Linux
```

### Expected Local Results

With 4 simulated local workers on a modern laptop:

```
Single machine:  ~30-40 seconds
Static (4):      ~10-12 seconds  (3-4x speedup)
Dynamic (4):     ~9-11 seconds   (3.5-4.5x speedup)
```

---

## Jetstream Testing

Test on actual distributed VMs.

### Prerequisites

1. **Complete Jetstream setup** (see [JETSTREAM_SETUP.md](JETSTREAM_SETUP.md))
2. **NFS configured** on all nodes
3. **Code deployed** to all nodes
4. **config.yaml updated** with worker IPs

### SSH to Master

```bash
ssh -i ~/.ssh/jetstream_key ubuntu@<master_ip>
cd ~/video_processing
```

### Create Test Videos

**Small test (30 seconds):**
```bash
ffmpeg -f lavfi -i testsrc=duration=30:size=1280x720:rate=30 \
       -pix_fmt yuv420p -c:v libx264 \
       -y /home/ubuntu/nfs_shared/test_small.mp4
```

**Medium test (2 minutes):**
```bash
ffmpeg -f lavfi -i testsrc=duration=120:size=1920x1080:rate=30 \
       -pix_fmt yuv420p -c:v libx264 \
       -y /home/ubuntu/nfs_shared/test_medium.mp4
```

**Large test (5 minutes):**
```bash
ffmpeg -f lavfi -i testsrc=duration=300:size=1920x1080:rate=30 \
       -pix_fmt yuv420p -c:v libx264 \
       -y /home/ubuntu/nfs_shared/test_large.mp4
```

### Run Tests

**Static scheduling:**
```bash
python3 src/main.py \
    --input /home/ubuntu/nfs_shared/test_medium.mp4 \
    --strategy static \
    --config config/config.yaml \
    --remote
```

**Dynamic scheduling:**
```bash
python3 src/main.py \
    --input /home/ubuntu/nfs_shared/test_medium.mp4 \
    --strategy dynamic \
    --config config/config.yaml \
    --remote
```

### Monitor Progress

**In another terminal (while test runs):**
```bash
# Watch processed files appear
watch -n 1 'ls -lh /home/ubuntu/nfs_shared/processed/'

# Check worker load
ssh -i ~/.ssh/jetstream_key ubuntu@<worker1_ip> 'top -n 1 | head -20'
```

### Verify NFS is Working

**Test file sharing:**
```bash
# On master
echo "test from master" > /home/ubuntu/nfs_shared/test.txt

# On worker1
ssh -i ~/.ssh/jetstream_key ubuntu@<worker1_ip>
cat /home/ubuntu/nfs_shared/test.txt
# Should output: test from master
```

### Expected Jetstream Results

With 4 workers (m3.medium VMs):

```
Small video (30s):
  Static:  ~8-12 seconds
  Dynamic: ~7-10 seconds

Medium video (2min):
  Static:  ~35-45 seconds
  Dynamic: ~30-40 seconds

Large video (5min):
  Static:  ~90-110 seconds
  Dynamic: ~80-100 seconds
```

---

## Performance Benchmarking

### Benchmark Script

Create `benchmark.sh`:

```bash
#!/bin/bash

VIDEO="/home/ubuntu/nfs_shared/test_medium.mp4"
RESULTS="benchmark_results.txt"

echo "Video Processing Benchmark" > $RESULTS
echo "===========================" >> $RESULTS
echo "" >> $RESULTS

# Test static
echo "Testing Static Scheduling..." | tee -a $RESULTS
START=$(date +%s)
python3 src/main.py --input $VIDEO --strategy static --remote
END=$(date +%s)
STATIC_TIME=$((END - START))
echo "Static: ${STATIC_TIME}s" | tee -a $RESULTS

# Cleanup
rm -rf /home/ubuntu/nfs_shared/{chunks,processed}/*
sleep 5

# Test dynamic
echo "Testing Dynamic Scheduling..." | tee -a $RESULTS
START=$(date +%s)
python3 src/main.py --input $VIDEO --strategy dynamic --remote
END=$(date +%s)
DYNAMIC_TIME=$((END - START))
echo "Dynamic: ${DYNAMIC_TIME}s" | tee -a $RESULTS

# Calculate speedup
echo "" >> $RESULTS
echo "Comparison:" >> $RESULTS
echo "Dynamic vs Static: $(echo "scale=2; $STATIC_TIME / $DYNAMIC_TIME" | bc)x" >> $RESULTS

cat $RESULTS
```

**Run:**
```bash
chmod +x benchmark.sh
./benchmark.sh
```

### Measure Speedup

**Formula:**
```
Speedup = Time_single_machine / Time_parallel
Efficiency = Speedup / num_workers * 100%
```

**Example calculation:**
```
Single machine: 120 seconds
Static (4 workers): 35 seconds
Dynamic (4 workers): 30 seconds

Static Speedup: 120 / 35 = 3.43x
Static Efficiency: 3.43 / 4 * 100 = 85.75%

Dynamic Speedup: 120 / 30 = 4.0x
Dynamic Efficiency: 4.0 / 4 * 100 = 100%
```

### Test Different Worker Counts

**Edit config.yaml to test with 1, 2, 4, 8 workers:**

```bash
# Test with 1 worker
# Update config.yaml: workers: [worker1]
python3 src/main.py --input video.mp4 --strategy dynamic --remote

# Test with 2 workers
# Update config.yaml: workers: [worker1, worker2]
python3 src/main.py --input video.mp4 --strategy dynamic --remote

# Test with 4 workers
# Update config.yaml: workers: [worker1, worker2, worker3, worker4]
python3 src/main.py --input video.mp4 --strategy dynamic --remote
```

**Create scalability graph:**
```
Workers | Time (s) | Speedup | Efficiency
--------|----------|---------|------------
1       | 120      | 1.0x    | 100%
2       | 65       | 1.85x   | 92.5%
4       | 35       | 3.43x   | 85.75%
8       | 20       | 6.0x    | 75%
```

---

## Validation

### Check Video Quality

**Compare input and output:**
```bash
# Get input info
ffprobe -v error -show_format -show_streams test_input.mp4

# Get output info
ffprobe -v error -show_format -show_streams final_dynamic.mp4

# Check durations match
# Check resolution matches
# Check frame rate matches
```

### Visual Inspection

```bash
# Download outputs
scp -i ~/.ssh/jetstream_key ubuntu@<master_ip>:/home/ubuntu/nfs_shared/output/*.mp4 .

# Play side-by-side
open test_input.mp4 &
open final_dynamic.mp4 &

# Or use ffplay
ffplay test_input.mp4 &
ffplay final_dynamic.mp4 &
```

### Verify All Segments Processed

```bash
# Count chunks
ls /home/ubuntu/nfs_shared/chunks/ | wc -l

# Count processed
ls /home/ubuntu/nfs_shared/processed/ | wc -l

# Should be equal!
```

### Check for Artifacts

Look for:
- ❌ Stuttering at segment boundaries
- ❌ Audio sync issues
- ❌ Frame drops
- ❌ Quality degradation
- ✅ Smooth playback
- ✅ Consistent quality

---

## Comparison Testing

### Compare All Three Implementations

**1. Main implementation (thread simulation):**
```bash
cd ../src
python3 main.py --input video.mp4 --strategy dynamic --workers 4
```

**2. SSH/SCP implementation:**
```bash
cd ../distributed-ssh-implementation/framework
python3 src/main.py --input video.mp4 --mode dynamic
```

**3. Hybrid NFS+SSH implementation:**
```bash
cd ../hybrid-nfs-implementation
python3 src/main.py --input video.mp4 --strategy dynamic --remote
```

### Create Comparison Table

| Implementation | Time (s) | Speedup | Notes |
|----------------|----------|---------|-------|
| Thread-based (local) | 120 | 1.0x | Baseline |
| SSH/SCP (cloud) | 55 | 2.18x | File transfer overhead |
| **NFS+SSH (cloud)** | **30** | **4.0x** | Zero file transfer |

### Key Metrics to Compare

1. **Total processing time**
2. **Network bandwidth used**
3. **Storage overhead**
4. **Fault tolerance**
5. **Ease of deployment**
6. **Code complexity**
7. **Scalability**

---

## Stress Testing

### Test Fault Tolerance

**Kill a worker mid-processing:**
```bash
# Start processing
python3 src/main.py --input video.mp4 --strategy dynamic --remote &

# Wait a few seconds, then kill a worker
ssh -i ~/.ssh/jetstream_key ubuntu@<worker2_ip> 'sudo killall ffmpeg'

# Dynamic scheduling should retry on another worker
# Check that processing completes successfully
```

### Test Large Videos

```bash
# Create 10-minute video
ffmpeg -f lavfi -i testsrc=duration=600:size=1920x1080:rate=30 \
       -pix_fmt yuv420p -c:v libx264 \
       -y /home/ubuntu/nfs_shared/test_10min.mp4

# Process
python3 src/main.py \
    --input /home/ubuntu/nfs_shared/test_10min.mp4 \
    --strategy dynamic \
    --remote
```

### Test Concurrent Jobs

```bash
# Run multiple jobs simultaneously
python3 src/main.py --input video1.mp4 --strategy dynamic --remote &
python3 src/main.py --input video2.mp4 --strategy dynamic --remote &

# Monitor resource usage
watch -n 1 'ssh ubuntu@<worker1_ip> top -n 1 | head -20'
```

---

## Test Checklist

Before considering testing complete:

- [ ] Local testing works (static and dynamic)
- [ ] Jetstream deployment successful
- [ ] NFS mounts verified on all workers
- [ ] Static scheduling completes successfully
- [ ] Dynamic scheduling completes successfully
- [ ] Output videos play correctly
- [ ] No visual artifacts in output
- [ ] Speedup measurements recorded
- [ ] Different worker counts tested
- [ ] Fault tolerance verified (worker failure)
- [ ] Performance compared with other implementations
- [ ] Documentation updated with results

---

## Troubleshooting Tests

### Test Fails Locally

```bash
# Check FFmpeg
ffmpeg -version

# Check config
cat config/config.yaml

# Check temp directory
ls -la /tmp/video_processing/

# Run with verbose Python
python3 -v src/main.py --input test.mp4 --strategy dynamic
```

### Test Fails on Jetstream

```bash
# Check NFS mounts
df -h | grep nfs_shared

# Check SSH connectivity
for i in 1 2 3 4; do
    echo "Testing worker$i..."
    ssh -i ~/.ssh/jetstream_key ubuntu@<worker${i}_ip> 'echo OK'
done

# Check FFmpeg on workers
ssh -i ~/.ssh/jetstream_key ubuntu@<worker1_ip> 'ffmpeg -version'

# Check file visibility
ls -lh /home/ubuntu/nfs_shared/chunks/
ssh -i ~/.ssh/jetstream_key ubuntu@<worker1_ip> 'ls -lh /home/ubuntu/nfs_shared/chunks/'
# Should show same files!
```

### Performance Lower Than Expected

```bash
# Check network latency
ping -c 5 <master_ip>

# Check disk I/O
dd if=/dev/zero of=/home/ubuntu/nfs_shared/test bs=1M count=1000

# Check CPU usage
ssh ubuntu@<worker1_ip> 'mpstat 1 10'

# Check if workers are actually being used
watch -n 1 'for i in 1 2 3 4; do echo "Worker $i:"; ssh ubuntu@worker${i} "ps aux | grep ffmpeg"; done'
```

---

## Reporting Results

### Create Results Summary

```markdown
# Test Results Summary

## Environment
- **Master:** m3.medium (6 vCPUs, 16GB RAM)
- **Workers:** 4× m3.medium
- **Network:** Jetstream2 internal
- **Storage:** NFS over 10Gbps network

## Test Videos
| Video | Duration | Resolution | Size |
|-------|----------|------------|------|
| Small | 30s | 1280×720 | 12MB |
| Medium | 2min | 1920×1080 | 85MB |
| Large | 5min | 1920×1080 | 210MB |

## Performance Results
| Strategy | Workers | Time (s) | Speedup | Efficiency |
|----------|---------|----------|---------|------------|
| Static | 1 | 120 | 1.0× | 100% |
| Static | 2 | 65 | 1.85× | 92.5% |
| Static | 4 | 35 | 3.43× | 85.75% |
| Dynamic | 1 | 120 | 1.0× | 100% |
| Dynamic | 2 | 60 | 2.0× | 100% |
| Dynamic | 4 | 30 | 4.0× | 100% |

## Key Findings
- Dynamic scheduling achieves better load balance
- NFS eliminates file transfer overhead
- Near-linear speedup up to 4 workers
- Efficiency remains above 85% with 4 workers
```

---

**Happy testing! 🧪🎬**
