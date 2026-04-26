#!/bin/bash

# Local testing script - runs without Jetstream
# Uses LocalWorker for simulation

set -e

echo "========================================"
echo "Local Testing (No Jetstream Required)"
echo "========================================"

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check FFmpeg
if ! command -v ffmpeg &> /dev/null; then
    echo "Error: FFmpeg not found!"
    echo "Install with: brew install ffmpeg"
    exit 1
fi

echo -e "${GREEN}✓ FFmpeg found${NC}"

# Create test video if needed
TEST_VIDEO="test_videos/test_input.mp4"

if [ ! -f "$TEST_VIDEO" ]; then
    echo -e "${YELLOW}Creating test video...${NC}"
    mkdir -p test_videos
    ffmpeg -f lavfi -i testsrc=duration=15:size=1280x720:rate=30 \
           -pix_fmt yuv420p -c:v libx264 -y $TEST_VIDEO
    echo -e "${GREEN}✓ Test video created${NC}"
fi

# Run static scheduling (local)
echo ""
echo -e "${YELLOW}=== Testing Static Scheduling ===${NC}"
python3 src/main.py \
    --input $TEST_VIDEO \
    --strategy static \
    --config config/config.yaml

# Run dynamic scheduling (local)
echo ""
echo -e "${YELLOW}=== Testing Dynamic Scheduling ===${NC}"
python3 src/main.py \
    --input $TEST_VIDEO \
    --strategy dynamic \
    --config config/config.yaml

echo ""
echo -e "${GREEN}========================================"
echo "✓ Local Testing Complete!"
echo "========================================${NC}"
echo ""
echo "Check outputs in /tmp/video_processing/output/"
echo ""
