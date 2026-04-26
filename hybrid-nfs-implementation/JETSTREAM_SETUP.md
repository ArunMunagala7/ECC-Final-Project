# Complete Jetstream2 Setup Guide

This guide walks you through setting up the hybrid NFS+SSH distributed video processing system on Jetstream2 from scratch.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Jetstream2 Account Setup](#jetstream2-account-setup)
3. [VM Provisioning](#vm-provisioning)
4. [SSH Key Configuration](#ssh-key-configuration)
5. [NFS Server Setup (Master Node)](#nfs-server-setup-master-node)
6. [NFS Client Setup (Worker Nodes)](#nfs-client-setup-worker-nodes)
7. [Code Deployment](#code-deployment)
8. [Configuration](#configuration)
9. [Testing](#testing)
10. [Troubleshooting](#troubleshooting)

---

## Prerequisites

**Local Machine:**
- macOS or Linux
- SSH client
- Python 3.8+
- FFmpeg installed (`brew install ffmpeg`)

**Estimated Total Time:** 1-2 hours

---

## Jetstream2 Account Setup

### Step 1: Get Access to Jetstream2

**Option A: Through XSEDE/ACCESS**
1. Go to https://access-ci.org/
2. Click "Get Your ACCESS ID"
3. Register with your university email
4. Wait for approval (usually 24-48 hours)

**Option B: Through Your Institution**
1. Check if your university has Jetstream2 allocation
2. Contact your professor or IT department
3. Request addition to existing allocation

**Option C: Request Startup Allocation**
1. Go to https://allocations.access-ci.org/
2. Login with ACCESS credentials
3. Request "Explore ACCESS" allocation (free, instant)
4. Select Jetstream2 as resource

### Step 2: Access Jetstream2 Dashboard

1. Go to https://jetstream2.exosphere.app/
2. Login with ACCESS credentials
3. Select your allocation/project

**You should now see the Exosphere dashboard.**

---

## VM Provisioning

You'll create **1 master + 4 worker VMs** (5 total).

### Step 3: Create Master Node

1. **Click "Create" → "Instance"**

2. **Configure Master:**
   - **Name:** `video-master`
   - **Image Source:** Featured → Ubuntu 22.04
   - **Instance Size:** m3.medium (6 vCPUs, 16GB RAM)
   - **Advanced Options:**
     - Enable "Allocate Public IP"
     - Security Groups: default

3. **Click "Create"**

4. **Wait 2-3 minutes** for instance to become "Ready"

5. **Note the Public IP** (e.g., `149.165.XXX.XXX`)

### Step 4: Create Worker Nodes

Repeat for each worker (4 times):

1. **Click "Create" → "Instance"**

2. **Configure Worker:**
   - **Name:** `video-worker1` (then worker2, worker3, worker4)
   - **Image Source:** Featured → Ubuntu 22.04
   - **Instance Size:** m3.medium (6 vCPUs, 16GB RAM)
   - **Advanced Options:**
     - Enable "Allocate Public IP"
     - Security Groups: default

3. **Click "Create"**

4. **Note each Worker IP**

### Example IP Setup:
```
Master:  149.165.170.10
Worker1: 149.165.170.11
Worker2: 149.165.170.12
Worker3: 149.165.170.13
Worker4: 149.165.170.14
```

**Tip:** Keep these IPs in a text file!

---

## SSH Key Configuration

### Step 5: Download SSH Key

1. **In Exosphere, go to "Account" → "SSH Public Keys"**

2. **Find your key** (Exosphere auto-creates one)

3. **Download private key:**
   - On VM details page, find "SSH access instructions"
   - Copy the private key content
   - Save to `~/.ssh/jetstream_key` on your local machine

4. **Set permissions:**
   ```bash
   chmod 600 ~/.ssh/jetstream_key
   ```

### Step 6: Test SSH Access

```bash
# Test master connection
ssh -i ~/.ssh/jetstream_key ubuntu@149.165.170.10

# If successful, you'll see Ubuntu prompt
# Exit with: exit
```

Test each worker similarly.

### Step 7: Setup SSH Config (Optional but Recommended)

Add to `~/.ssh/config`:

```
Host jetstream-master
    HostName 149.165.170.10
    User ubuntu
    IdentityFile ~/.ssh/jetstream_key
    StrictHostKeyChecking no

Host jetstream-worker1
    HostName 149.165.170.11
    User ubuntu
    IdentityFile ~/.ssh/jetstream_key
    StrictHostKeyChecking no

Host jetstream-worker2
    HostName 149.165.170.12
    User ubuntu
    IdentityFile ~/.ssh/jetstream_key
    StrictHostKeyChecking no

Host jetstream-worker3
    HostName 149.165.170.13
    User ubuntu
    IdentityFile ~/.ssh/jetstream_key
    StrictHostKeyChecking no

Host jetstream-worker4
    HostName 149.165.170.14
    User ubuntu
    IdentityFile ~/.ssh/jetstream_key
    StrictHostKeyChecking no
```

Now you can SSH with: `ssh jetstream-master`

---

## NFS Server Setup (Master Node)

### Step 8: Configure NFS on Master

**SSH into master:**
```bash
ssh -i ~/.ssh/jetstream_key ubuntu@<master_ip>
```

**Upload and run NFS server script:**

From your **local machine**:
```bash
cd hybrid-nfs-implementation

# Copy script to master
scp -i ~/.ssh/jetstream_key scripts/nfs_server_setup.sh ubuntu@<master_ip>:~/

# SSH into master and run
ssh -i ~/.ssh/jetstream_key ubuntu@<master_ip>

# On master, run setup
sudo bash nfs_server_setup.sh
```

**The script will:**
- Install NFS server packages
- Create `/home/ubuntu/nfs_shared` directory
- Configure NFS exports
- Start NFS services
- Configure firewall rules

**Verify NFS is running:**
```bash
showmount -e localhost
# Should show: /home/ubuntu/nfs_shared *
```

---

## NFS Client Setup (Worker Nodes)

### Step 9: Mount NFS on Each Worker

**For each worker, SSH in and run:**

From your **local machine**:
```bash
# Copy script to worker
scp -i ~/.ssh/jetstream_key scripts/nfs_client_setup.sh ubuntu@<worker_ip>:~/

# SSH into worker
ssh -i ~/.ssh/jetstream_key ubuntu@<worker_ip>

# On worker, run setup (replace with actual master IP)
sudo bash nfs_client_setup.sh 149.165.170.10
```

**The script will:**
- Install NFS client packages
- Create mount point
- Mount NFS share from master
- Add to `/etc/fstab` for persistent mount

**Verify mount:**
```bash
df -h | grep nfs_shared
# Should show: 149.165.170.10:/home/ubuntu/nfs_shared
```

**Test file sharing:**

On **master**:
```bash
echo "test" > /home/ubuntu/nfs_shared/test.txt
```

On **worker1**:
```bash
cat /home/ubuntu/nfs_shared/test.txt
# Should output: test
```

If you see "test", NFS is working! 🎉

---

## Code Deployment

### Step 10: Deploy Code to All Nodes

From your **local machine** in the `hybrid-nfs-implementation/` directory:

```bash
cd scripts

# Edit deploy.sh to set your IPs or run interactively
./deploy.sh
```

**You'll be prompted to enter:**
- Master IP
- Worker IPs (space-separated)

**The script will:**
- Copy source code to all nodes
- Install FFmpeg on all nodes
- Install Python dependencies
- Verify NFS mounts

**Manual deployment alternative:**

If deploy.sh doesn't work, manually copy code:

```bash
# To master
scp -i ~/.ssh/jetstream_key -r src config ubuntu@<master_ip>:~/video_processing/

# To each worker
scp -i ~/.ssh/jetstream_key -r src config ubuntu@<worker1_ip>:~/video_processing/
# Repeat for worker2, worker3, worker4
```

Then SSH to each node and install dependencies:
```bash
sudo apt-get update
sudo apt-get install -y ffmpeg python3-pip
pip3 install pyyaml
```

---

## Configuration

### Step 11: Update Configuration File

**On your local machine**, edit `config/config.yaml`:

```yaml
# Update with your actual worker IPs
workers:
  - host: "149.165.170.11"  # worker1
  - host: "149.165.170.12"  # worker2
  - host: "149.165.170.13"  # worker3
  - host: "149.165.170.14"  # worker4

ssh_user: "ubuntu"
ssh_key: "~/.ssh/jetstream_key"
nfs_base_dir: "/home/ubuntu/nfs_shared"
```

**Upload updated config to master:**
```bash
scp -i ~/.ssh/jetstream_key config/config.yaml ubuntu@<master_ip>:~/video_processing/config/
```

---

## Testing

### Step 12: Create Test Video

**SSH into master:**
```bash
ssh -i ~/.ssh/jetstream_key ubuntu@<master_ip>
cd ~/video_processing
```

**Create test video:**
```bash
# Generate 30-second test video
ffmpeg -f lavfi -i testsrc=duration=30:size=1280x720:rate=30 \
       -pix_fmt yuv420p -c:v libx264 -y /home/ubuntu/nfs_shared/test_input.mp4
```

### Step 13: Run Static Scheduling Test

```bash
python3 src/main.py \
    --input /home/ubuntu/nfs_shared/test_input.mp4 \
    --strategy static \
    --config config/config.yaml \
    --remote
```

**You should see:**
- Segmentation progress
- Worker assignments
- Processing progress
- Merge completion
- Final statistics

### Step 14: Run Dynamic Scheduling Test

```bash
python3 src/main.py \
    --input /home/ubuntu/nfs_shared/test_input.mp4 \
    --strategy dynamic \
    --config config/config.yaml \
    --remote
```

### Step 15: Verify Output

```bash
# Check output files
ls -lh /home/ubuntu/nfs_shared/output/

# Play output (download to local machine first)
exit  # Exit from master

# On local machine
scp -i ~/.ssh/jetstream_key ubuntu@<master_ip>:/home/ubuntu/nfs_shared/output/final_dynamic.mp4 .

# Open with video player
open final_dynamic.mp4  # macOS
```

---

## Troubleshooting

### Problem: Cannot SSH to VM

**Solution:**
```bash
# Check SSH key permissions
chmod 600 ~/.ssh/jetstream_key

# Try verbose mode
ssh -v -i ~/.ssh/jetstream_key ubuntu@<vm_ip>

# Check VM is running in Exosphere dashboard
```

### Problem: NFS Mount Fails

**Solution:**
```bash
# On master, check NFS is running
sudo systemctl status nfs-kernel-server
showmount -e localhost

# On worker, try manual mount
sudo mount -v master_ip:/home/ubuntu/nfs_shared /home/ubuntu/nfs_shared

# Check firewall
sudo ufw status
```

### Problem: Workers Can't Access NFS

**Solution:**
```bash
# On master, check exports
cat /etc/exports
sudo exportfs -v

# Restart NFS server
sudo systemctl restart nfs-kernel-server

# On worker, remount
sudo umount /home/ubuntu/nfs_shared
sudo mount master_ip:/home/ubuntu/nfs_shared /home/ubuntu/nfs_shared
```

### Problem: FFmpeg Not Found

**Solution:**
```bash
# On each node
sudo apt-get update
sudo apt-get install -y ffmpeg
ffmpeg -version
```

### Problem: SSH Connection Timeout

**Solution:**
```bash
# Check VM public IP hasn't changed (Jetstream can reassign)
# In Exosphere, verify IPs
# Update config.yaml with new IPs
```

### Problem: "Permission Denied" on NFS

**Solution:**
```bash
# On master, fix permissions
sudo chown -R ubuntu:ubuntu /home/ubuntu/nfs_shared
sudo chmod -R 755 /home/ubuntu/nfs_shared
```

---

## Performance Testing

### Step 16: Benchmark Different Strategies

```bash
# SSH to master
ssh -i ~/.ssh/jetstream_key ubuntu@<master_ip>
cd ~/video_processing

# Create larger test video (2 minutes)
ffmpeg -f lavfi -i testsrc=duration=120:size=1920x1080:rate=30 \
       -pix_fmt yuv420p -c:v libx264 -y /home/ubuntu/nfs_shared/large_test.mp4

# Test with different worker counts
# 1 worker
python3 src/main.py --input /home/ubuntu/nfs_shared/large_test.mp4 \
    --strategy dynamic --config config/config.yaml --remote

# Update config to use 2, 4, 8 workers and rerun
```

---

## Cleanup

### Step 17: Stop VMs (Save Allocation)

When done testing:

1. **In Exosphere dashboard**
2. **Click each instance → "Actions" → "Shelve"**
3. This stops billing but preserves VM state
4. "Unshelve" to resume later

### Step 18: Delete VMs (Complete Cleanup)

If completely done:

1. **In Exosphere dashboard**
2. **Click each instance → "Actions" → "Delete"**
3. Confirm deletion
4. This frees all resources

---

## Cost Estimation

**Jetstream2 Service Unit (SU) Usage:**
- m3.medium: ~6 SUs/hour
- 5 VMs × 6 SUs = 30 SUs/hour
- 1 hour testing = 30 SUs
- 5 hours testing = 150 SUs

**ACCESS Explore allocation: 400,000 SUs (plenty for this project!)**

---

## Next Steps

✅ You now have a fully working distributed video processing system!

**Try:**
1. Process real videos
2. Compare static vs. dynamic performance
3. Benchmark with different worker counts
4. Measure speedup and efficiency
5. Test fault tolerance (kill a worker mid-processing)

**For your report:**
- Save benchmark results
- Take screenshots of processing
- Document speedup calculations
- Compare with local implementation

---

## Quick Reference Commands

```bash
# SSH to master
ssh -i ~/.ssh/jetstream_key ubuntu@<master_ip>

# Check NFS mounts
df -h | grep nfs_shared

# Run processing
python3 src/main.py --input video.mp4 --strategy dynamic --remote

# Monitor workers
watch -n 1 'ls -lh /home/ubuntu/nfs_shared/processed/'

# Check logs
tail -f /home/ubuntu/video_processing/logs/processing.log
```

---

## Support Resources

- **Jetstream2 Documentation:** https://docs.jetstream-cloud.org/
- **ACCESS Support:** https://support.access-ci.org/
- **NFS Guide:** https://ubuntu.com/server/docs/service-nfs
- **Our Project README:** See `README.md` in this directory

---

**Good luck with your distributed video processing! 🚀🎬**
