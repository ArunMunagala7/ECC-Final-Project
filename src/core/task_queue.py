"""
Task queue management for distributed video processing
"""

import json
import time
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
from threading import Lock
from .logger import LoggerMixin


class TaskStatus(Enum):
    """Task execution status"""
    PENDING = "pending"
    ASSIGNED = "assigned"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Task:
    """Represents a processing task"""
    task_id: str
    segment_id: int
    input_path: str
    output_path: str
    start_time: float
    duration: float
    status: TaskStatus = TaskStatus.PENDING
    worker_id: Optional[str] = None
    assigned_at: Optional[float] = None
    completed_at: Optional[float] = None
    error: Optional[str] = None
    retry_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary"""
        data = asdict(self)
        data['status'] = self.status.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Task':
        """Create task from dictionary"""
        data['status'] = TaskStatus(data['status'])
        return cls(**data)


class TaskQueue(LoggerMixin):
    """Thread-safe task queue for managing work distribution"""
    
    def __init__(self):
        self.tasks: Dict[str, Task] = {}
        self.pending_queue: List[str] = []  # Task IDs
        self.lock = Lock()
    
    def add_task(self, task: Task):
        """Add a task to the queue"""
        with self.lock:
            self.tasks[task.task_id] = task
            if task.status == TaskStatus.PENDING:
                self.pending_queue.append(task.task_id)
        self.logger.debug(f"Added task {task.task_id}")
    
    def add_tasks(self, tasks: List[Task]):
        """Add multiple tasks to the queue"""
        with self.lock:
            for task in tasks:
                self.tasks[task.task_id] = task
                if task.status == TaskStatus.PENDING:
                    self.pending_queue.append(task.task_id)
        self.logger.info(f"Added {len(tasks)} tasks to queue")
    
    def get_next_task(self, worker_id: str) -> Optional[Task]:
        """
        Get next available task for a worker
        
        Args:
            worker_id: ID of the requesting worker
            
        Returns:
            Next available task or None if queue is empty
        """
        with self.lock:
            if not self.pending_queue:
                return None
            
            task_id = self.pending_queue.pop(0)
            task = self.tasks[task_id]
            task.status = TaskStatus.ASSIGNED
            task.worker_id = worker_id
            task.assigned_at = time.time()
            
        self.logger.info(f"Assigned task {task_id} to worker {worker_id}")
        return task
    
    def mark_processing(self, task_id: str):
        """Mark task as currently being processed"""
        with self.lock:
            if task_id in self.tasks:
                self.tasks[task_id].status = TaskStatus.PROCESSING
        self.logger.debug(f"Task {task_id} now processing")
    
    def mark_completed(self, task_id: str):
        """Mark task as completed"""
        with self.lock:
            if task_id in self.tasks:
                task = self.tasks[task_id]
                task.status = TaskStatus.COMPLETED
                task.completed_at = time.time()
        self.logger.info(f"Task {task_id} completed")
    
    def mark_failed(self, task_id: str, error: str, max_retries: int = 3):
        """
        Mark task as failed and optionally requeue for retry
        
        Args:
            task_id: Task identifier
            error: Error message
            max_retries: Maximum number of retry attempts
        """
        with self.lock:
            if task_id in self.tasks:
                task = self.tasks[task_id]
                task.retry_count += 1
                task.error = error
                
                if task.retry_count < max_retries:
                    # Requeue for retry
                    task.status = TaskStatus.PENDING
                    task.worker_id = None
                    task.assigned_at = None
                    self.pending_queue.append(task_id)
                    self.logger.warning(
                        f"Task {task_id} failed (attempt {task.retry_count}/{max_retries}), requeuing"
                    )
                else:
                    task.status = TaskStatus.FAILED
                    self.logger.error(f"Task {task_id} failed after {max_retries} attempts: {error}")
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """Get task by ID"""
        with self.lock:
            return self.tasks.get(task_id)
    
    def get_all_tasks(self) -> List[Task]:
        """Get all tasks"""
        with self.lock:
            return list(self.tasks.values())
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get queue statistics"""
        with self.lock:
            total = len(self.tasks)
            pending = sum(1 for t in self.tasks.values() if t.status == TaskStatus.PENDING)
            assigned = sum(1 for t in self.tasks.values() if t.status == TaskStatus.ASSIGNED)
            processing = sum(1 for t in self.tasks.values() if t.status == TaskStatus.PROCESSING)
            completed = sum(1 for t in self.tasks.values() if t.status == TaskStatus.COMPLETED)
            failed = sum(1 for t in self.tasks.values() if t.status == TaskStatus.FAILED)
            
            return {
                'total': total,
                'pending': pending,
                'assigned': assigned,
                'processing': processing,
                'completed': completed,
                'failed': failed,
                'in_queue': len(self.pending_queue)
            }
    
    def is_complete(self) -> bool:
        """Check if all tasks are completed or failed"""
        with self.lock:
            for task in self.tasks.values():
                if task.status not in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                    return False
            return len(self.tasks) > 0
    
    def save_state(self, filepath: str):
        """Save queue state to file"""
        with self.lock:
            state = {
                'tasks': [t.to_dict() for t in self.tasks.values()],
                'pending_queue': self.pending_queue
            }
        
        with open(filepath, 'w') as f:
            json.dump(state, f, indent=2)
        self.logger.info(f"Queue state saved to {filepath}")
    
    def load_state(self, filepath: str):
        """Load queue state from file"""
        with open(filepath, 'r') as f:
            state = json.load(f)
        
        with self.lock:
            self.tasks = {
                t['task_id']: Task.from_dict(t) 
                for t in state['tasks']
            }
            self.pending_queue = state['pending_queue']
        
        self.logger.info(f"Queue state loaded from {filepath}")
