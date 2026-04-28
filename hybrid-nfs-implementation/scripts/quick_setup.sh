#!/bin/bash

# Quick Jetstream Setup Script
# Run this after creating your VMs

echo "=========================================="
echo "Jetstream Quick Setup"
echo "=========================================="
echo ""

# Get IPs from user
read -p "Enter MASTER IP: " MASTER_IP
read -p "Enter WORKER1 IP: " WORKER1_IP
read -p "Enter WORKER2 IP: " WORKER2_IP
read -p "Enter WORKER3 IP: " WORKER3_IP
read -p "Enter WORKER4 IP: " WORKER4_IP
read -p "Enter USERNAME (ubuntu or exouser): " SSH_USER

WORKERS=($WORKER1_IP $WORKER2_IP $WORKER3_IP $WORKER4_IP)

echo ""
echo "Configuration:"
echo "  Master: $MASTER_IP"
echo "  Workers: ${WORKERS[@]}"
echo "  Username: $SSH_USER"
echo ""
read -p "Press Enter to continue or Ctrl+C to cancel..."

# Step 1: Setup NFS on master
echo ""
echo "=== Step 1: Setting up NFS server on master ==="
echo ""

ssh ${SSH_USER}@${MASTER_IP} << 'ENDSSH'
# Update and install NFS server
sudo apt-get update
sudo apt-get install -y nfs-kernel-server

# Create NFS directory
sudo mkdir -p /home/ubuntu/nfs_shared/{chunks,processed,output}
sudo chown -R ubuntu:ubuntu /home/ubuntu/nfs_shared
sudo chmod -R 755 /home/ubuntu/nfs_shared

# Configure NFS exports
echo "/home/ubuntu/nfs_shared *(rw,sync,no_subtree_check,no_root_squash)" | sudo tee -a /etc/exports

# Apply and start NFS
sudo exportfs -ra
sudo systemctl restart nfs-kernel-server
sudo systemctl enable nfs-kernel-server

# Show status
echo "NFS server setup complete!"
sudo showmount -e localhost
ENDSSH

echo "✓ Master NFS server ready"

# Step 2: Setup NFS clients on workers
echo ""
echo "=== Step 2: Mounting NFS on workers ==="
echo ""

for i in "${!WORKERS[@]}"; do
    WORKER_IP=${WORKERS[$i]}
    echo "Setting up worker $((i+1)): $WORKER_IP"
    
    ssh ${SSH_USER}@${WORKER_IP} << ENDSSH
# Install NFS client
sudo apt-get update
sudo apt-get install -y nfs-common

# Create mount point
sudo mkdir -p /home/ubuntu/nfs_shared

# Mount NFS share
sudo mount ${MASTER_IP}:/home/ubuntu/nfs_shared /home/ubuntu/nfs_shared

# Add to fstab for persistence
echo "${MASTER_IP}:/home/ubuntu/nfs_shared /home/ubuntu/nfs_shared nfs defaults 0 0" | sudo tee -a /etc/fstab

# Verify mount
df -h | grep nfs_shared
ENDSSH
    
    echo "✓ Worker $((i+1)) mounted NFS"
done

# Step 3: Install dependencies on all nodes
echo ""
echo "=== Step 3: Installing FFmpeg and dependencies ==="
echo ""

for NODE in $MASTER_IP "${WORKERS[@]}"; do
    echo "Installing on $NODE..."
    ssh ${SSH_USER}@${NODE} << 'ENDSSH'
sudo apt-get install -y ffmpeg python3-pip
pip3 install pyyaml
ENDSSH
done

echo ""
echo "=========================================="
echo "✓ Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Update config/config.yaml with your worker IPs"
echo "2. Deploy code with: ./scripts/deploy.sh"
echo "3. Run test on master VM"
echo ""
