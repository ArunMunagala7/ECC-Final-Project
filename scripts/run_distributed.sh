#!/bin/bash

# Script to run distributed processing on Jetstream2

set -e

# Default configuration
MASTER_HOST="${MASTER_HOST:-master-node}"
WORKER_HOSTS="${WORKER_HOSTS:-worker-1 worker-2}"
SSH_KEY="${SSH_KEY:-~/.ssh/jetstream2_key}"
PROJECT_DIR="${PROJECT_DIR:-/home/ubuntu/video-processing}"

# Parse arguments
INPUT_VIDEO=""
OUTPUT_VIDEO=""
STRATEGY="dynamic"
NUM_WORKERS=2

while [[ $# -gt 0 ]]; do
    case $1 in
        --input)
            INPUT_VIDEO="$2"
            shift 2
            ;;
        --output)
            OUTPUT_VIDEO="$2"
            shift 2
            ;;
        --strategy)
            STRATEGY="$2"
            shift 2
            ;;
        --workers)
            NUM_WORKERS="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

if [ -z "$INPUT_VIDEO" ]; then
    echo "Error: --input is required"
    echo "Usage: $0 --input video.mp4 [--output result.mp4] [--strategy dynamic] [--workers 2]"
    exit 1
fi

OUTPUT_VIDEO="${OUTPUT_VIDEO:-output/result.mp4}"

echo "========================================"
echo "Distributed Processing on Jetstream2"
echo "========================================"
echo "Master: $MASTER_HOST"
echo "Workers: $WORKER_HOSTS"
echo "Input: $INPUT_VIDEO"
echo "Output: $OUTPUT_VIDEO"
echo "Strategy: $STRATEGY"
echo "Workers: $NUM_WORKERS"
echo "========================================"

# Upload input video to master
echo "Uploading input video to master..."
scp -i "$SSH_KEY" "$INPUT_VIDEO" "ubuntu@$MASTER_HOST:$PROJECT_DIR/storage/input/"

INPUT_FILENAME=$(basename "$INPUT_VIDEO")

# Run processing on master
echo "Starting distributed processing..."
ssh -i "$SSH_KEY" "ubuntu@$MASTER_HOST" << EOF
    cd $PROJECT_DIR
    python3 src/main.py \
        --input storage/input/$INPUT_FILENAME \
        --output storage/$OUTPUT_VIDEO \
        --strategy $STRATEGY \
        --workers $NUM_WORKERS
EOF

# Download result
echo "Downloading result..."
scp -i "$SSH_KEY" "ubuntu@$MASTER_HOST:$PROJECT_DIR/storage/$OUTPUT_VIDEO" .

echo "========================================"
echo "Processing Complete!"
echo "Output: $OUTPUT_VIDEO"
echo "========================================"
