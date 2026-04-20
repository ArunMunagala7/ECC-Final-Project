"""
Evaluation and metrics module
Handles performance measurement and analysis
"""

import os
import sys
import json
import time
from typing import Dict, List, Any, Optional
from datetime import datetime
import matplotlib.pyplot as plt

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.logger import LoggerMixin, setup_logger
from core.config import Config


class PerformanceMetrics(LoggerMixin):
    """Collect and analyze performance metrics"""
    
    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()
        log_dir = self.config.get('logging', 'log_dir', default='logs')
        log_level = self.config.get('logging', 'level', default='INFO')
        self._logger = setup_logger("Metrics", log_level=log_level, log_dir=log_dir)
        
        self.metrics_dir = self.config.get('evaluation', 'metrics_dir', default='metrics')
        os.makedirs(self.metrics_dir, exist_ok=True)
    
    def calculate_speedup(
        self,
        baseline_time: float,
        distributed_time: float
    ) -> float:
        """
        Calculate speedup factor
        
        Args:
            baseline_time: Single-machine processing time
            distributed_time: Distributed processing time
            
        Returns:
            Speedup factor
        """
        if distributed_time == 0:
            return 0.0
        return baseline_time / distributed_time
    
    def calculate_efficiency(
        self,
        speedup: float,
        num_workers: int
    ) -> float:
        """
        Calculate parallel efficiency
        
        Args:
            speedup: Speedup factor
            num_workers: Number of workers
            
        Returns:
            Efficiency (0 to 1)
        """
        if num_workers == 0:
            return 0.0
        return speedup / num_workers
    
    def analyze_load_balance(
        self,
        worker_stats: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """
        Analyze load balancing across workers
        
        Args:
            worker_stats: List of worker statistics
            
        Returns:
            Load balance metrics
        """
        if not worker_stats:
            return {'balance_score': 0.0, 'variance': 0.0}
        
        tasks_per_worker = [w['tasks_completed'] for w in worker_stats]
        
        if not tasks_per_worker:
            return {'balance_score': 0.0, 'variance': 0.0}
        
        mean_tasks = sum(tasks_per_worker) / len(tasks_per_worker)
        variance = sum((x - mean_tasks) ** 2 for x in tasks_per_worker) / len(tasks_per_worker)
        
        # Balance score: 1.0 = perfect balance, 0.0 = poor balance
        max_tasks = max(tasks_per_worker) if tasks_per_worker else 1
        min_tasks = min(tasks_per_worker) if tasks_per_worker else 0
        balance_score = min_tasks / max_tasks if max_tasks > 0 else 0.0
        
        return {
            'balance_score': balance_score,
            'variance': variance,
            'mean_tasks': mean_tasks,
            'min_tasks': min_tasks,
            'max_tasks': max_tasks,
            'tasks_per_worker': tasks_per_worker
        }
    
    def save_metrics(
        self,
        experiment_name: str,
        metrics: Dict[str, Any]
    ):
        """
        Save metrics to JSON file
        
        Args:
            experiment_name: Name of the experiment
            metrics: Metrics dictionary
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{experiment_name}_{timestamp}.json"
        filepath = os.path.join(self.metrics_dir, filename)
        
        with open(filepath, 'w') as f:
            json.dump(metrics, f, indent=2)
        
        self.logger.info(f"Metrics saved to {filepath}")
        return filepath
    
    def load_metrics(self, filepath: str) -> Dict[str, Any]:
        """Load metrics from JSON file"""
        with open(filepath, 'r') as f:
            return json.load(f)
    
    def generate_comparison_report(
        self,
        results: List[Dict[str, Any]],
        output_file: Optional[str] = None
    ) -> str:
        """
        Generate comparison report from multiple results
        
        Args:
            results: List of experiment results
            output_file: Output file path (auto-generated if None)
            
        Returns:
            Path to generated report
        """
        if output_file is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = os.path.join(self.metrics_dir, f'comparison_report_{timestamp}.txt')
        
        with open(output_file, 'w') as f:
            f.write("=" * 80 + "\n")
            f.write("Video Processing Performance Comparison Report\n")
            f.write("=" * 80 + "\n\n")
            
            for result in results:
                strategy = result.get('strategy', 'Unknown')
                f.write(f"\nStrategy: {strategy}\n")
                f.write("-" * 80 + "\n")
                f.write(f"Workers: {result.get('num_workers', 'N/A')}\n")
                f.write(f"Total Time: {result.get('total_time', 0):.2f}s\n")
                f.write(f"Tasks Completed: {result.get('tasks_completed', 0)}\n")
                f.write(f"Tasks Failed: {result.get('tasks_failed', 0)}\n")
                
                if 'speedup' in result:
                    f.write(f"Speedup: {result['speedup']:.2f}x\n")
                
                if 'efficiency' in result:
                    f.write(f"Efficiency: {result['efficiency']:.2%}\n")
                
                if 'load_balance' in result:
                    lb = result['load_balance']
                    f.write(f"Load Balance Score: {lb.get('balance_score', 0):.2f}\n")
                
                f.write("\n")
        
        self.logger.info(f"Report generated: {output_file}")
        return output_file


class PerformanceVisualizer:
    """Create visualizations for performance metrics"""
    
    def __init__(self, output_dir: str = 'metrics'):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def plot_speedup(
        self,
        workers: List[int],
        speedups: List[float],
        output_file: Optional[str] = None
    ):
        """
        Plot speedup vs number of workers
        
        Args:
            workers: List of worker counts
            speedups: Corresponding speedup values
            output_file: Output file path
        """
        if output_file is None:
            output_file = os.path.join(self.output_dir, 'speedup_plot.png')
        
        plt.figure(figsize=(10, 6))
        plt.plot(workers, speedups, marker='o', linewidth=2, markersize=8, label='Actual Speedup')
        plt.plot(workers, workers, '--', linewidth=2, label='Ideal Linear Speedup')
        plt.xlabel('Number of Workers', fontsize=12)
        plt.ylabel('Speedup', fontsize=12)
        plt.title('Speedup vs Number of Workers', fontsize=14)
        plt.grid(True, alpha=0.3)
        plt.legend(fontsize=10)
        plt.tight_layout()
        plt.savefig(output_file, dpi=300)
        plt.close()
        
        return output_file
    
    def plot_strategy_comparison(
        self,
        strategies: List[str],
        times: List[float],
        output_file: Optional[str] = None
    ):
        """
        Compare processing times across strategies
        
        Args:
            strategies: List of strategy names
            times: Corresponding processing times
            output_file: Output file path
        """
        if output_file is None:
            output_file = os.path.join(self.output_dir, 'strategy_comparison.png')
        
        plt.figure(figsize=(10, 6))
        bars = plt.bar(strategies, times, color=['#1f77b4', '#ff7f0e', '#2ca02c'])
        plt.xlabel('Strategy', fontsize=12)
        plt.ylabel('Processing Time (seconds)', fontsize=12)
        plt.title('Processing Time Comparison', fontsize=14)
        plt.grid(True, axis='y', alpha=0.3)
        
        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.2f}s',
                    ha='center', va='bottom', fontsize=10)
        
        plt.tight_layout()
        plt.savefig(output_file, dpi=300)
        plt.close()
        
        return output_file
    
    def plot_load_balance(
        self,
        worker_ids: List[str],
        tasks_completed: List[int],
        output_file: Optional[str] = None
    ):
        """
        Visualize load balance across workers
        
        Args:
            worker_ids: List of worker identifiers
            tasks_completed: Tasks completed by each worker
            output_file: Output file path
        """
        if output_file is None:
            output_file = os.path.join(self.output_dir, 'load_balance.png')
        
        plt.figure(figsize=(10, 6))
        plt.bar(worker_ids, tasks_completed, color='#2ca02c')
        plt.xlabel('Worker ID', fontsize=12)
        plt.ylabel('Tasks Completed', fontsize=12)
        plt.title('Load Distribution Across Workers', fontsize=14)
        plt.grid(True, axis='y', alpha=0.3)
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        plt.savefig(output_file, dpi=300)
        plt.close()
        
        return output_file
