"""
Benchmark script for comparing processing strategies
"""

import os
import sys
import argparse
from typing import List, Dict, Any
import time

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from core.config import Config
from core.logger import setup_logger
from master import Master
from main import process_single_machine
from evaluation import PerformanceMetrics, PerformanceVisualizer


def run_benchmark(
    input_path: str,
    worker_counts: List[int],
    config: Config
) -> List[Dict[str, Any]]:
    """
    Run comprehensive benchmark across strategies
    
    Args:
        input_path: Path to input video
        worker_counts: List of worker counts to test
        config: Configuration object
        
    Returns:
        List of benchmark results
    """
    logger = setup_logger("Benchmark", log_level='INFO')
    results = []
    
    output_dir = config.get_storage_path('output', 'benchmark')
    os.makedirs(output_dir, exist_ok=True)
    
    # Test 1: Single machine baseline
    logger.info("Running single-machine baseline...")
    output_path = os.path.join(output_dir, 'single_output.mp4')
    baseline_result = process_single_machine(input_path, output_path, config)
    results.append(baseline_result)
    baseline_time = baseline_result['total_time']
    
    # Test 2: Static partitioning with various worker counts
    for num_workers in worker_counts:
        if num_workers == 1:
            continue  # Skip, already tested as baseline
        
        logger.info(f"Running static partitioning with {num_workers} workers...")
        output_path = os.path.join(output_dir, f'static_{num_workers}w_output.mp4')
        
        master = Master(config)
        result = master.process_static(
            input_path=input_path,
            output_path=output_path,
            num_workers=num_workers
        )
        result['strategy'] = f'static_{num_workers}w'
        
        # Calculate speedup
        metrics = PerformanceMetrics(config)
        result['speedup'] = metrics.calculate_speedup(baseline_time, result['total_time'])
        result['efficiency'] = metrics.calculate_efficiency(result['speedup'], num_workers)
        result['load_balance'] = metrics.analyze_load_balance(result.get('worker_stats', []))
        
        results.append(result)
    
    # Test 3: Dynamic scheduling with various worker counts
    for num_workers in worker_counts:
        if num_workers == 1:
            continue
        
        logger.info(f"Running dynamic scheduling with {num_workers} workers...")
        output_path = os.path.join(output_dir, f'dynamic_{num_workers}w_output.mp4')
        
        master = Master(config)
        result = master.process_dynamic(
            input_path=input_path,
            output_path=output_path,
            num_workers=num_workers
        )
        result['strategy'] = f'dynamic_{num_workers}w'
        
        # Calculate metrics
        metrics = PerformanceMetrics(config)
        result['speedup'] = metrics.calculate_speedup(baseline_time, result['total_time'])
        result['efficiency'] = metrics.calculate_efficiency(result['speedup'], num_workers)
        result['load_balance'] = metrics.analyze_load_balance(result.get('worker_stats', []))
        
        results.append(result)
    
    return results


def main():
    """Main benchmark execution"""
    parser = argparse.ArgumentParser(description='Benchmark Video Processing Framework')
    parser.add_argument('--input', required=True, help='Path to input video')
    parser.add_argument(
        '--workers',
        default='1,2,4',
        help='Comma-separated list of worker counts to test (default: 1,2,4)'
    )
    parser.add_argument('--config', default=None, help='Path to config file')
    
    args = parser.parse_args()
    
    # Parse worker counts
    worker_counts = [int(w.strip()) for w in args.workers.split(',')]
    
    # Load config
    config = Config(args.config) if args.config else Config()
    logger = setup_logger("Benchmark", log_level='INFO')
    
    logger.info("=" * 80)
    logger.info("Starting Comprehensive Benchmark")
    logger.info("=" * 80)
    logger.info(f"Input Video: {args.input}")
    logger.info(f"Worker Counts: {worker_counts}")
    logger.info("=" * 80)
    
    # Run benchmarks
    start_time = time.time()
    results = run_benchmark(args.input, worker_counts, config)
    total_time = time.time() - start_time
    
    logger.info(f"\nBenchmark completed in {total_time:.2f}s")
    
    # Generate report
    metrics = PerformanceMetrics(config)
    report_path = metrics.generate_comparison_report(results)
    logger.info(f"Report saved to: {report_path}")
    
    # Save detailed results
    metrics_path = metrics.save_metrics("comprehensive_benchmark", {
        'results': results,
        'total_benchmark_time': total_time,
        'worker_counts': worker_counts
    })
    logger.info(f"Detailed metrics saved to: {metrics_path}")
    
    # Generate visualizations
    visualizer = PerformanceVisualizer(config.get('evaluation', 'metrics_dir', default='metrics'))
    
    # Extract data for plots
    strategies = [r['strategy'] for r in results]
    times = [r['total_time'] for r in results]
    
    # Plot 1: Strategy comparison
    viz_path = visualizer.plot_strategy_comparison(strategies, times)
    logger.info(f"Strategy comparison plot: {viz_path}")
    
    # Plot 2: Speedup for dynamic scheduling
    dynamic_results = [r for r in results if 'dynamic' in r['strategy'] and 'speedup' in r]
    if dynamic_results:
        workers = [r['num_workers'] for r in dynamic_results]
        speedups = [r['speedup'] for r in dynamic_results]
        viz_path = visualizer.plot_speedup(workers, speedups)
        logger.info(f"Speedup plot: {viz_path}")
    
    logger.info("=" * 80)
    logger.info("Benchmark Summary")
    logger.info("=" * 80)
    for result in results:
        logger.info(f"{result['strategy']:20s} - {result['total_time']:6.2f}s", end='')
        if 'speedup' in result:
            logger.info(f" - Speedup: {result['speedup']:.2f}x - Efficiency: {result['efficiency']:.1%}")
        else:
            logger.info("")
    logger.info("=" * 80)


if __name__ == '__main__':
    main()
