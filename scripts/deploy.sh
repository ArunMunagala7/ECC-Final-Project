#!/bin/bash

# Deployment script for Jetstream2 cloud infrastructure

set -e

echo "========================================"
echo "Jetstream2 Deployment Script"
echo "========================================"

# Configuration
MASTER_HOST="${MASTER_HOST:-master-node}"
WORKER_HOSTS="${WORKER_HOSTS:-worker-1 worker-2}"
PROJECT_DIR="${PROJECT_DIR:-/home/ubuntu/video-processing}"
SSH_KEY="${SSH_KEY:-~/.ssh/jetstream2_key}"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "Configuration:"
echo "  Master: $MASTER_HOST"
echo "  Workers: $WORKER_HOSTS"
echo "  Project Dir: $PROJECT_DIR"
echo ""

# Function to deploy to a node
deploy_to_node() {
    local host=$1
    echo -e "${YELLOW}Deploying to $host...${NC}"
    
    # Copy project files
    rsync -avz -e "ssh -i $SSH_KEY" \
        --exclude 'storage/' \
        --exclude 'logs/' \
        --exclude 'metrics/' \
        --exclude '__pycache__/' \
        --exclude '*.pyc' \
        ./ "ubuntu@$host:$PROJECT_DIR/"
    
    # Install dependencies
    ssh -i "$SSH_KEY" "ubuntu@$host" << 'EOF'
        cd $PROJECT_DIR
        
        # Update system
        sudo apt-get update -qq
        
        # Install FFmpeg if not present
        if ! command -v ffmpeg &> /dev/null; then
            echo "Installing FFmpeg..."
            sudo apt-get install -y ffmpeg
        fi
        
        # Install Python dependencies
        pip3 install -r requirements.txt -q
        
        echo "Node setup complete"
EOF
    
    echo -e "${GREEN}✓ $host deployed${NC}"
}

# Deploy to master
echo ""
echo "Deploying to master node..."
deploy_to_node "$MASTER_HOST"

# Deploy to workers
echo ""
echo "Deploying to worker nodes..."
for worker in $WORKER_HOSTS; do
    deploy_to_node "$worker"
done

echo ""
echo -e "${GREEN}Deployment Complete!${NC}"
echo ""
echo "Next steps:"
echo "1. Setup shared storage (NFS) on all nodes"
echo "2. Configure config/config.yaml for remote storage paths"
echo "3. Run distributed processing with scripts/run_distributed.sh"
echo ""
