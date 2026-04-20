"""
Worker node implementation
Handles video segment processing
"""

import os
import sys
import time
import uuid
from typing import Optional

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.logger import LoggerMixin, setup_logger
from core.config import Config
from core.processor import VideoProcessor
from core.task_queue import Task, TaskStatus


class Worker(LoggerMixin):
    """Worker node for distributed video processing"""
    
    def __init__(
        self,
        worker_id: Optional[str] = None,
        config: Optional[Config] = None
    ):
        """
        Initialize worker
        
        Args:
            worker_id: Unique worker identifier (auto-generated if None)
            config: Configuration object
        """
        self.worker_id = worker_id or f"worker_{uuid.uuid4().hex[:8]}"
        self.config = config or Config()
        
        # Setup logger
        log_dir = self.config.get('logging', 'log_dir', default='logs')
        log_level = self.config.get('logging', 'level', default='INFO')
        self._logger = setup_logger(
            f"Worker-{self.worker_id}",
            log_level=log_level,
            log_dir=log_dir
        )
        
        # Initialize processor
        proc_config = self.config.get('processing', default={})
        self.processor = VideoProcessor(
            codec=proc_config.get('codec', 'libx264'),
            crf=proc_config.get('crf', 23),
            preset=proc_config.get('preset', 'medium'),
            scale=proc_config.get('scale'),
            bitrate=proc_config.get('bitrate')
        )
        
        self.is_running = False
        self.current_task: Optional[Task] = None
        self.tasks_completed = 0
        self.tasks_failed = 0
        
        self.logger.info(f"Worker {self.worker_id} initialized")
    
    def process_task(self, task: Task) -> bool:
        """
        Process a single task
        
        Args:
            task: Task to process
            
        Returns:
            True if successful, False otherwise
        """
        self.current_task = task
        self.logger.info(f"Processing task {task.task_id} (segment {task.segment_id})")
        
        start_time = time.time()
        
        try:
            # Ensure output directory exists
            os.makedirs(os.path.dirname(task.output_path), exist_ok=True)
            
            # Process the video segment
            self.processor.process_segment(
                input_path=task.input_path,
                output_path=task.output_path,
                start_time=task.start_time,
                duration=task.duration
            )
            
            elapsed = time.time() - start_time
            self.logger.info(
                f"Task {task.task_id} completed in {elapsed:.2f}s"
            )
            
            self.tasks_completed += 1
            self.current_task = None
            return True
            
        except Exception as e:
            elapsed = time.time() - start_time
            self.logger.error(
                f"Task {task.task_id} failed after {elapsed:.2f}s: {e}"
            )
            self.tasks_failed += 1
            self.current_task = None
            return False
    
    def get_status(self) -> dict:
        """Get worker status"""
        return {
            'worker_id': self.worker_id,
            'is_running': self.is_running,
            'current_task': self.current_task.task_id if self.current_task else None,
            'tasks_completed': self.tasks_completed,
            'tasks_failed': self.tasks_failed
        }
    
    def shutdown(self):
        """Shutdown worker gracefully"""
        self.logger.info(f"Worker {self.worker_id} shutting down")
        self.is_running = False
