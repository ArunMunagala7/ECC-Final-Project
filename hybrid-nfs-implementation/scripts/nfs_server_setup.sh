#!/bin/bash

# NFS Setup Script for Jetstream2
# Run this on the master node to configure NFS server

set -e

echo "========================================"
echo "NFS Server Setup for Master Node"
echo "========================================"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# NFS directory
NFS_DIR="/home/ubuntu/nfs_shared"

# Check if running as root or with sudo
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Please run as root or with sudo${NC}"
    exit 1
fi

echo -e "${GREEN}Step 1: Installing NFS server${NC}"
apt-get update
apt-get install -y nfs-kernel-server

echo -e "${GREEN}Step 2: Creating NFS directory${NC}"
mkdir -p ${NFS_DIR}/chunks
mkdir -p ${NFS_DIR}/processed
mkdir -p ${NFS_DIR}/output
chown -R ubuntu:ubuntu ${NFS_DIR}
chmod -R 755 ${NFS_DIR}

echo -e "${GREEN}Step 3: Configuring NFS exports${NC}"
# Backup existing exports
if [ -f /etc/exports ]; then
    cp /etc/exports /etc/exports.backup
fi

# Add NFS export (allows all IPs - restrict in production)
echo "${NFS_DIR} *(rw,sync,no_subtree_check,no_root_squash)" >> /etc/exports

echo -e "${GREEN}Step 4: Applying NFS configuration${NC}"
exportfs -ra

echo -e "${GREEN}Step 5: Starting NFS services${NC}"
systemctl restart nfs-kernel-server
systemctl enable nfs-kernel-server

echo -e "${GREEN}Step 6: Configuring firewall${NC}"
# Allow NFS through firewall
ufw allow from any to any port 2049
ufw allow from any to any port 111

echo ""
echo -e "${GREEN}✓ NFS server setup complete!${NC}"
echo ""
echo "NFS export: ${NFS_DIR}"
echo ""
echo "To mount on worker nodes, run:"
echo -e "${YELLOW}sudo mkdir -p ${NFS_DIR}${NC}"
echo -e "${YELLOW}sudo mount <master_ip>:${NFS_DIR} ${NFS_DIR}${NC}"
echo ""
echo "Or use the nfs_client_setup.sh script on each worker"
echo ""

# Show NFS status
echo -e "${GREEN}NFS Status:${NC}"
showmount -e localhost
