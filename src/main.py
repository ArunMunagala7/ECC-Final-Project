"""
Main entry point for distributed video processing
"""

import os
import sys
import argparse
import time
from typing import Dict, Any

# Add src directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.config import Config
from core.processor import VideoProcessor
from core.logger import setup_logger
from master import Master


def process_single_machine(
    input_path: str,
    output_path: str,
    config: Config
) -> Dict[str, Any]:
    """
    Process video on single machine (baseline)
    
    Args:
        input_path: Path to input video
        output_path: Path for output video
        config: Configuration object
        
    Returns:
        Processing statistics
    """
    logger = setup_logger("SingleMachine", log_level=config.get('logging', 'level', default='INFO'))
    logger.info("Starting single-machine processing")
    
    start_time = time.time()
    
    # Initialize processor
    proc_config = config.get('processing', default={})
    processor = VideoProcessor(
        codec=proc_config.get('codec', 'libx264'),
        crf=proc_config.get('crf', 23),
        preset=proc_config.get('preset', 'medium'),
        scale=proc_config.get('scale'),
        bitrate=proc_config.get('bitrate')
    )
    
    # Check FFmpeg
    if not processor.check_ffmpeg():
        logger.error("FFmpeg not found! Please install FFmpeg.")
        sys.exit(1)
    
    # Process entire video
    processor.process_segment(input_path, output_path)
    
    end_time = time.time()
    total_time = end_time - start_time
    
    logger.info(f"Single-machine processing completed in {total_time:.2f}s")
    
    return {
        'strategy': 'single',
        'num_workers': 1,
        'total_time': total_time,
        'tasks_completed': 1,
        'tasks_failed': 0
    }


def main():
    """Main execution function"""
    parser = argparse.ArgumentParser(
        description='Distributed Video Processing Framework'
    )
    parser.add_argument(
        '--input',
        required=True,
        help='Path to input video file'
    )
    parser.add_argument(
        '--output',
        required=True,
        help='Path for output video file'
    )
    parser.add_argument(
        '--workers',
        type=int,
        default=2,
        help='Number of worker threads (default: 2)'
    )
    parser.add_argument(
        '--strategy',
        choices=['single', 'static', 'dynamic'],
        default='dynamic',
        help='Processing strategy (default: dynamic)'
    )
    parser.add_argument(
        '--segments',
        type=int,
        default=None,
        help='Number of segments (default: auto based on chunk_duration)'
    )
    parser.add_argument(
        '--config',
        default=None,
        help='Path to configuration file'
    )
    
    args = parser.parse_args()
    
    # Load configuration
    config = Config(args.config) if args.config else Config()
    
    # Setup logger
    logger = setup_logger(
        "Main",
        log_level=config.get('logging', 'level', default='INFO'),
        log_dir=config.get('logging', 'log_dir', default='logs')
    )
    
    # Validate input
    if not os.path.exists(args.input):
        logger.error(f"Input file not found: {args.input}")
        sys.exit(1)
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    
    logger.info("=" * 80)
    logger.info("Elastic Distributed Video Processing Framework")
    logger.info("=" * 80)
    logger.info(f"Input: {args.input}")
    logger.info(f"Output: {args.output}")
    logger.info(f"Strategy: {args.strategy}")
    logger.info(f"Workers: {args.workers}")
    logger.info("=" * 80)
    
    # Execute processing based on strategy
    try:
        if args.strategy == 'single':
            stats = process_single_machine(args.input, args.output, config)
        else:
            master = Master(config)
            
            if args.strategy == 'static':
                stats = master.process_static(
                    input_path=args.input,
                    output_path=args.output,
                    num_workers=args.workers
                )
            else:  # dynamic
                stats = master.process_dynamic(
                    input_path=args.input,
                    output_path=args.output,
                    num_workers=args.workers,
                    num_segments=args.segments
                )
        
        # Print results
        logger.info("=" * 80)
        logger.info("Processing Complete!")
        logger.info("=" * 80)
        logger.info(f"Strategy: {stats['strategy']}")
        logger.info(f"Total Time: {stats['total_time']:.2f}s")
        logger.info(f"Workers: {stats['num_workers']}")
        logger.info(f"Tasks Completed: {stats['tasks_completed']}")
        logger.info(f"Tasks Failed: {stats['tasks_failed']}")
        logger.info("=" * 80)
        
        # Save metrics
        from evaluation import PerformanceMetrics
        metrics = PerformanceMetrics(config)
        metrics.save_metrics(f"{args.strategy}_processing", stats)
        
    except Exception as e:
        logger.error(f"Processing failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
