"""
Main entry point for hybrid NFS+SSH distributed video processing
"""

import sys
import os
import argparse
import yaml
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.master import Master
from src.worker import RemoteWorker, LocalWorker
from src.core.processor import VideoProcessor


def load_config(config_path):
    """Load configuration from YAML file"""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def create_workers(config, use_remote=False):
    """
    Create worker instances based on config
    
    Args:
        config: Configuration dict
        use_remote: If True, create RemoteWorker instances for Jetstream
                   If False, create LocalWorker instances for testing
    """
    worker_configs = config.get('workers', [])
    workers = []
    
    if use_remote:
        # Create remote workers for Jetstream deployment
        ssh_key = config.get('ssh_key')
        ssh_user = config.get('ssh_user', 'ubuntu')
        
        for i, worker_config in enumerate(worker_configs):
            worker = RemoteWorker(
                worker_id=i,
                ssh_host=worker_config['host'],
                ssh_user=ssh_user,
                ssh_key=ssh_key
            )
            workers.append(worker)
            print(f"Created RemoteWorker {i}: {worker_config['host']}")
    else:
        # Create local workers for testing
        num_workers = len(worker_configs) or 4
        for i in range(num_workers):
            worker = LocalWorker(worker_id=i)
            workers.append(worker)
            print(f"Created LocalWorker {i}")
    
    return workers


def main():
    parser = argparse.ArgumentParser(
        description='Hybrid NFS+SSH Distributed Video Processing'
    )
    parser.add_argument(
        '--input',
        required=True,
        help='Input video file path'
    )
    parser.add_argument(
        '--strategy',
        choices=['static', 'dynamic'],
        default='dynamic',
        help='Scheduling strategy (default: dynamic)'
    )
    parser.add_argument(
        '--config',
        default='config/config.yaml',
        help='Configuration file path'
    )
    parser.add_argument(
        '--remote',
        action='store_true',
        help='Use remote Jetstream workers (default: local testing)'
    )
    
    args = parser.parse_args()
    
    # Check FFmpeg
    if not VideoProcessor.check_ffmpeg():
        print("ERROR: FFmpeg not found! Please install FFmpeg.")
        print("  macOS: brew install ffmpeg")
        print("  Ubuntu: sudo apt-get install -y ffmpeg")
        return 1
    
    print("✓ FFmpeg found")
    
    # Load configuration
    config_path = Path(__file__).parent.parent / args.config
    if not config_path.exists():
        print(f"ERROR: Config file not found: {config_path}")
        return 1
    
    config = load_config(config_path)
    print(f"✓ Loaded config from {config_path}")
    
    # Check input video
    if not os.path.exists(args.input):
        print(f"ERROR: Input video not found: {args.input}")
        return 1
    
    print(f"✓ Input video: {args.input}")
    
    # Create workers
    print(f"\n{'='*60}")
    print(f"Mode: {'REMOTE (Jetstream)' if args.remote else 'LOCAL (Testing)'}")
    print(f"Strategy: {args.strategy.upper()}")
    print(f"{'='*60}\n")
    
    workers = create_workers(config, use_remote=args.remote)
    
    if not workers:
        print("ERROR: No workers created!")
        return 1
    
    print(f"✓ Created {len(workers)} workers\n")
    
    # Create master and process
    master = Master(config)
    
    if args.strategy == 'static':
        stats = master.process_static(args.input, workers)
    else:
        stats = master.process_dynamic(args.input, workers)
    
    # Print summary
    print(f"\n{'='*60}")
    print(f"PROCESSING SUMMARY")
    print(f"{'='*60}")
    print(f"Strategy: {stats['strategy']}")
    print(f"Workers: {stats['num_workers']}")
    print(f"Segments: {stats['num_segments']}")
    print(f"Successful: {stats['successful']}")
    print(f"Failed: {stats['failed']}")
    print(f"Total time: {stats['total_time']:.2f}s")
    print(f"Output: {stats['output_path']}")
    print(f"{'='*60}\n")
    
    # Worker statistics
    print("Worker Statistics:")
    for worker_stat in stats['worker_stats']:
        print(f"  Worker {worker_stat['worker_id']} ({worker_stat['ssh_host']}): "
              f"{worker_stat['tasks_completed']} completed, "
              f"{worker_stat['tasks_failed']} failed")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
