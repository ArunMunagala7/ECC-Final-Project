#!/bin/bash

# Demo script for local testing of the distributed video processing framework

set -e

echo "========================================"
echo "Video Processing Framework - Demo"
echo "========================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if FFmpeg is installed
if ! command -v ffmpeg &> /dev/null; then
    echo -e "${RED}Error: FFmpeg is not installed${NC}"
    echo "Please install FFmpeg:"
    echo "  brew install ffmpeg"
    exit 1
fi

echo -e "${GREEN}✓ FFmpeg found${NC}"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is not installed${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Python 3 found${NC}"

# Install dependencies
echo ""
echo "Installing Python dependencies..."
pip3 install -r requirements.txt -q

echo -e "${GREEN}✓ Dependencies installed${NC}"

# Create demo video if it doesn't exist
DEMO_DIR="demo"
mkdir -p "$DEMO_DIR"

DEMO_VIDEO="$DEMO_DIR/sample.mp4"

if [ ! -f "$DEMO_VIDEO" ]; then
    echo ""
    echo "Creating demo video..."
    # Generate a 30-second test video with FFmpeg
    ffmpeg -f lavfi -i testsrc=duration=30:size=1280x720:rate=30 \
           -f lavfi -i sine=frequency=1000:duration=30 \
           -pix_fmt yuv420p -c:v libx264 -preset fast \
           "$DEMO_VIDEO" -y &> /dev/null
    echo -e "${GREEN}✓ Demo video created: $DEMO_VIDEO${NC}"
else
    echo -e "${GREEN}✓ Demo video exists: $DEMO_VIDEO${NC}"
fi

# Create output directory
OUTPUT_DIR="output/demo"
mkdir -p "$OUTPUT_DIR"

echo ""
echo "========================================"
echo "Running Processing Tests"
echo "========================================"

# Test 1: Single machine baseline
echo ""
echo -e "${YELLOW}[1/3] Single Machine Processing${NC}"
python3 src/main.py \
    --input "$DEMO_VIDEO" \
    --output "$OUTPUT_DIR/single_output.mp4" \
    --strategy single

# Test 2: Static partitioning
echo ""
echo -e "${YELLOW}[2/3] Static Partitioning (2 workers)${NC}"
python3 src/main.py \
    --input "$DEMO_VIDEO" \
    --output "$OUTPUT_DIR/static_output.mp4" \
    --strategy static \
    --workers 2

# Test 3: Dynamic scheduling
echo ""
echo -e "${YELLOW}[3/3] Dynamic Scheduling (2 workers)${NC}"
python3 src/main.py \
    --input "$DEMO_VIDEO" \
    --output "$OUTPUT_DIR/dynamic_output.mp4" \
    --strategy dynamic \
    --workers 2

echo ""
echo "========================================"
echo -e "${GREEN}Demo Complete!${NC}"
echo "========================================"
echo "Output videos are in: $OUTPUT_DIR"
echo "Logs are in: logs/"
echo "Metrics are in: metrics/"
echo ""
echo "To run a comprehensive benchmark:"
echo "  python3 src/evaluation/benchmark.py --input $DEMO_VIDEO --workers 1,2,4"
echo ""
