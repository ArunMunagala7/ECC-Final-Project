#!/bin/bash

# Deployment script for Jetstream2
# Deploys code to all nodes and verifies setup

set -e

echo "========================================"
echo "Jetstream2 Deployment Script"
echo "========================================"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
SSH_KEY="${HOME}/.ssh/jetstream_key"
SSH_USER="ubuntu"
REMOTE_DIR="/home/ubuntu/video_processing"

# Read worker IPs from config
MASTER_IP=""
WORKER_IPS=()

echo -e "${YELLOW}Enter master node IP:${NC}"
read MASTER_IP

echo -e "${YELLOW}Enter worker node IPs (space-separated):${NC}"
read -a WORKER_IPS

if [ -z "$MASTER_IP" ]; then
    echo -e "${RED}Master IP required${NC}"
    exit 1
fi

if [ ${#WORKER_IPS[@]} -eq 0 ]; then
    echo -e "${RED}At least one worker IP required${NC}"
    exit 1
fi

echo ""
echo "Master: $MASTER_IP"
echo "Workers: ${WORKER_IPS[*]}"
echo ""

# Function to deploy to a node
deploy_to_node() {
    local ip=$1
    local node_type=$2
    
    echo -e "${GREEN}Deploying to $node_type: $ip${NC}"
    
    # Create remote directory
    ssh -i $SSH_KEY -o StrictHostKeyChecking=no $SSH_USER@$ip "mkdir -p $REMOTE_DIR"
    
    # Copy code
    rsync -avz -e "ssh -i $SSH_KEY -o StrictHostKeyChecking=no" \
        --exclude='*.pyc' \
        --exclude='__pycache__' \
        --exclude='.git' \
        --exclude='test_videos' \
        ../src/ $SSH_USER@$ip:$REMOTE_DIR/src/
    
    rsync -avz -e "ssh -i $SSH_KEY -o StrictHostKeyChecking=no" \
        ../config/ $SSH_USER@$ip:$REMOTE_DIR/config/
    
    # Install dependencies
    ssh -i $SSH_KEY $SSH_USER@$ip << 'EOF'
        # Install FFmpeg
        if ! command -v ffmpeg &> /dev/null; then
            echo "Installing FFmpeg..."
            sudo apt-get update
            sudo apt-get install -y ffmpeg
        fi
        
        # Install Python dependencies
        if ! command -v pip3 &> /dev/null; then
            echo "Installing pip..."
            sudo apt-get install -y python3-pip
        fi
        
        pip3 install pyyaml
        
        echo "✓ Dependencies installed"
EOF
    
    echo -e "${GREEN}✓ Deployment to $ip complete${NC}"
}

# Deploy to master
echo -e "\n${YELLOW}=== Deploying to Master ===${NC}"
deploy_to_node $MASTER_IP "master"

# Deploy to workers
for worker_ip in "${WORKER_IPS[@]}"; do
    echo -e "\n${YELLOW}=== Deploying to Worker ===${NC}"
    deploy_to_node $worker_ip "worker"
done

# Verify NFS mounts
echo -e "\n${YELLOW}=== Verifying NFS Mounts ===${NC}"

for worker_ip in "${WORKER_IPS[@]}"; do
    echo "Checking worker: $worker_ip"
    ssh -i $SSH_KEY $SSH_USER@$worker_ip "df -h | grep nfs_shared || echo 'WARNING: NFS not mounted'"
done

echo ""
echo -e "${GREEN}========================================"
echo "✓ Deployment Complete!"
echo "========================================${NC}"
echo ""
echo "Next steps:"
echo "1. Verify NFS is mounted on all workers"
echo "2. Update config/config.yaml with worker IPs"
echo "3. Run test: python3 src/main.py --input test.mp4 --strategy dynamic --remote"
echo ""
