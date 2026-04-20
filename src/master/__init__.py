"""
Master node implementation
Coordinates distributed video processing
"""

import os
import sys
import time
from typing import List, Optional, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.logger import LoggerMixin, setup_logger
from core.config import Config
from core.segmenter import VideoSegmenter, VideoSegment
from core.merger import VideoMerger
from core.task_queue import TaskQueue, Task, TaskStatus
from worker import Worker


class Master(LoggerMixin):
    """Master node for coordinating distributed video processing"""
    
    def __init__(self, config: Optional[Config] = None):
        """
        Initialize master node
        
        Args:
            config: Configuration object
        """
        self.config = config or Config()
        
        # Setup logger
        log_dir = self.config.get('logging', 'log_dir', default='logs')
        log_level = self.config.get('logging', 'level', default='INFO')
        self._logger = setup_logger(
            "Master",
            log_level=log_level,
            log_dir=log_dir
        )
        
        # Initialize components
        chunk_duration = self.config.get('segmentation', 'chunk_duration', default=10)
        self.segmenter = VideoSegmenter(chunk_duration=chunk_duration)
        self.merger = VideoMerger()
        self.task_queue = TaskQueue()
        
        self.workers: List[Worker] = []
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        
        self.logger.info("Master node initialized")
    
    def prepare_video(
        self,
        input_path: str,
        num_segments: Optional[int] = None
    ) -> List[VideoSegment]:
        """
        Prepare video for processing by creating segments
        
        Args:
            input_path: Path to input video
            num_segments: Number of segments (if None, uses chunk_duration)
            
        Returns:
            List of VideoSegment objects
        """
        self.logger.info(f"Preparing video: {input_path}")
        
        # Create output directory for chunks
        chunks_dir = self.config.get_storage_path('chunks')
        
        # Create segments
        segments = self.segmenter.create_segments(
            video_path=input_path,
            output_dir=chunks_dir,
            num_segments=num_segments
        )
        
        self.logger.info(f"Video prepared with {len(segments)} segments")
        return segments
    
    def create_tasks(self, segments: List[VideoSegment]) -> List[Task]:
        """
        Create tasks from video segments
        
        Args:
            segments: List of VideoSegment objects
            
        Returns:
            List of Task objects
        """
        tasks = []
        output_dir = self.config.get_storage_path('output', 'segments')
        os.makedirs(output_dir, exist_ok=True)
        
        for segment in segments:
            task = Task(
                task_id=f"task_{segment.segment_id:04d}",
                segment_id=segment.segment_id,
                input_path=segment.input_path,
                output_path=os.path.join(output_dir, f"processed_{segment.segment_id:04d}.mp4"),
                start_time=segment.start_time,
                duration=segment.duration,
                status=TaskStatus.PENDING
            )
            tasks.append(task)
        
        self.logger.info(f"Created {len(tasks)} tasks")
        return tasks
    
    def process_dynamic(
        self,
        input_path: str,
        output_path: str,
        num_workers: int = 2,
        num_segments: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Process video using dynamic queue-based scheduling
        
        Args:
            input_path: Path to input video
            output_path: Path for output video
            num_workers: Number of worker threads
            num_segments: Number of segments to create
            
        Returns:
            Processing statistics
        """
        self.start_time = time.time()
        self.logger.info(f"Starting dynamic processing with {num_workers} workers")
        
        # Step 1: Prepare video and create segments
        segments = self.prepare_video(input_path, num_segments)
        
        # Step 2: Create tasks and populate queue
        tasks = self.create_tasks(segments)
        self.task_queue.add_tasks(tasks)
        
        # Step 3: Create workers
        self.workers = [Worker(config=self.config) for _ in range(num_workers)]
        
        # Step 4: Process tasks in parallel
        self._process_tasks_parallel()
        
        # Step 5: Merge processed segments
        self.logger.info("Merging processed segments...")
        
        # Update segment output paths to point to processed files
        for i, segment in enumerate(segments):
            segment.output_path = tasks[i].output_path
        
        self.merger.merge_segments(segments, output_path)
        
        self.end_time = time.time()
        
        # Collect statistics
        stats = self._collect_statistics()
        stats['strategy'] = 'dynamic'
        self.logger.info(f"Processing completed in {stats['total_time']:.2f}s")
        
        return stats
    
    def _process_tasks_parallel(self):
        """Process tasks using thread pool"""
        def worker_process(worker: Worker):
            """Worker processing function"""
            worker.is_running = True
            processed = 0
            
            while True:
                # Get next task from queue
                task = self.task_queue.get_next_task(worker.worker_id)
                
                if task is None:
                    # No more tasks
                    break
                
                # Mark as processing
                self.task_queue.mark_processing(task.task_id)
                
                # Process task
                success = worker.process_task(task)
                
                if success:
                    self.task_queue.mark_completed(task.task_id)
                    processed += 1
                else:
                    max_retries = self.config.get('worker', 'max_retries', default=3)
                    self.task_queue.mark_failed(
                        task.task_id,
                        "Processing failed",
                        max_retries=max_retries
                    )
            
            worker.is_running = False
            self.logger.info(f"Worker {worker.worker_id} processed {processed} tasks")
        
        # Execute workers in thread pool
        with ThreadPoolExecutor(max_workers=len(self.workers)) as executor:
            futures = [
                executor.submit(worker_process, worker)
                for worker in self.workers
            ]
            
            # Wait for all workers to complete
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    self.logger.error(f"Worker error: {e}")
    
    def process_static(
        self,
        input_path: str,
        output_path: str,
        num_workers: int = 2
    ) -> Dict[str, Any]:
        """
        Process video using static partitioning
        
        Args:
            input_path: Path to input video
            output_path: Path for output video
            num_workers: Number of workers
            
        Returns:
            Processing statistics
        """
        self.start_time = time.time()
        self.logger.info(f"Starting static processing with {num_workers} workers")
        
        # Prepare video with segments equal to workers
        segments = self.prepare_video(input_path, num_segments=num_workers)
        tasks = self.create_tasks(segments)
        
        # Create workers
        self.workers = [Worker(config=self.config) for _ in range(num_workers)]
        
        # Assign tasks statically
        def process_assigned_tasks(worker: Worker, assigned_tasks: List[Task]):
            """Process pre-assigned tasks"""
            worker.is_running = True
            for task in assigned_tasks:
                self.logger.info(f"Worker {worker.worker_id} processing task {task.task_id}")
                worker.process_task(task)
            worker.is_running = False
        
        # Distribute tasks evenly
        tasks_per_worker = len(tasks) // num_workers
        
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = []
            for i, worker in enumerate(self.workers):
                start_idx = i * tasks_per_worker
                end_idx = start_idx + tasks_per_worker if i < num_workers - 1 else len(tasks)
                assigned = tasks[start_idx:end_idx]
                futures.append(executor.submit(process_assigned_tasks, worker, assigned))
            
            # Wait for completion
            for future in as_completed(futures):
                future.result()
        
        # Merge segments
        for i, segment in enumerate(segments):
            segment.output_path = tasks[i].output_path
        
        self.merger.merge_segments(segments, output_path)
        
        self.end_time = time.time()
        stats = self._collect_statistics()
        stats['strategy'] = 'static'
        
        return stats
    
    def _collect_statistics(self) -> Dict[str, Any]:
        """Collect processing statistics"""
        total_time = (self.end_time - self.start_time) if self.end_time else 0
        
        worker_stats = [w.get_status() for w in self.workers]
        total_completed = sum(w['tasks_completed'] for w in worker_stats)
        total_failed = sum(w['tasks_failed'] for w in worker_stats)
        
        return {
            'total_time': total_time,
            'num_workers': len(self.workers),
            'tasks_completed': total_completed,
            'tasks_failed': total_failed,
            'worker_stats': worker_stats,
            'queue_stats': self.task_queue.get_statistics()
        }
