#!/bin/bash

# NFS Client Setup Script for Jetstream2 Worker Nodes
# Run this on each worker node to mount NFS share

set -e

echo "========================================"
echo "NFS Client Setup for Worker Node"
echo "========================================"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check arguments
if [ $# -eq 0 ]; then
    echo -e "${RED}Usage: $0 <master_ip>${NC}"
    echo "Example: $0 149.165.XXX.XXX"
    exit 1
fi

MASTER_IP=$1
NFS_DIR="/home/ubuntu/nfs_shared"

# Check if running as root or with sudo
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Please run as root or with sudo${NC}"
    exit 1
fi

echo -e "${GREEN}Step 1: Installing NFS client${NC}"
apt-get update
apt-get install -y nfs-common

echo -e "${GREEN}Step 2: Creating mount point${NC}"
mkdir -p ${NFS_DIR}
chown ubuntu:ubuntu ${NFS_DIR}

echo -e "${GREEN}Step 3: Testing NFS connection${NC}"
showmount -e ${MASTER_IP}

echo -e "${GREEN}Step 4: Mounting NFS share${NC}"
mount -t nfs ${MASTER_IP}:${NFS_DIR} ${NFS_DIR}

# Verify mount
if mountpoint -q ${NFS_DIR}; then
    echo -e "${GREEN}✓ NFS mounted successfully!${NC}"
else
    echo -e "${RED}✗ NFS mount failed${NC}"
    exit 1
fi

echo -e "${GREEN}Step 5: Adding to /etc/fstab for persistent mount${NC}"
# Remove any existing entry
sed -i "\|${MASTER_IP}:${NFS_DIR}|d" /etc/fstab
# Add new entry
echo "${MASTER_IP}:${NFS_DIR} ${NFS_DIR} nfs defaults 0 0" >> /etc/fstab

echo ""
echo -e "${GREEN}✓ NFS client setup complete!${NC}"
echo ""
echo "Mount point: ${NFS_DIR}"
echo "NFS server: ${MASTER_IP}"
echo ""
echo "Verify with: df -h | grep nfs_shared"
echo ""

# Show mount info
df -h | grep nfs_shared
