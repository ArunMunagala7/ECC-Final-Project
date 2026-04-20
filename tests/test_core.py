"""
Test suite for video processing framework
"""

import os
import sys
import unittest
import tempfile
import shutil

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.core.config import Config
from src.core.segmenter import VideoSegmenter, VideoSegment
from src.core.task_queue import TaskQueue, Task, TaskStatus
from src.core.processor import VideoProcessor


class TestConfig(unittest.TestCase):
    """Test configuration management"""
    
    def test_config_loading(self):
        """Test loading configuration file"""
        config = Config()
        self.assertIsNotNone(config.config)
        self.assertIn('storage', config.config)
    
    def test_nested_get(self):
        """Test nested configuration access"""
        config = Config()
        chunk_duration = config.get('segmentation', 'chunk_duration', default=10)
        self.assertIsInstance(chunk_duration, (int, float))


class TestTaskQueue(unittest.TestCase):
    """Test task queue management"""
    
    def setUp(self):
        """Setup test queue"""
        self.queue = TaskQueue()
    
    def test_add_task(self):
        """Test adding tasks to queue"""
        task = Task(
            task_id='test_1',
            segment_id=0,
            input_path='/tmp/input.mp4',
            output_path='/tmp/output.mp4',
            start_time=0.0,
            duration=10.0
        )
        self.queue.add_task(task)
        self.assertEqual(len(self.queue.pending_queue), 1)
    
    def test_get_next_task(self):
        """Test fetching next task"""
        task = Task(
            task_id='test_1',
            segment_id=0,
            input_path='/tmp/input.mp4',
            output_path='/tmp/output.mp4',
            start_time=0.0,
            duration=10.0
        )
        self.queue.add_task(task)
        
        next_task = self.queue.get_next_task('worker_1')
        self.assertIsNotNone(next_task)
        self.assertEqual(next_task.status, TaskStatus.ASSIGNED)
        self.assertEqual(next_task.worker_id, 'worker_1')
    
    def test_mark_completed(self):
        """Test marking task as completed"""
        task = Task(
            task_id='test_1',
            segment_id=0,
            input_path='/tmp/input.mp4',
            output_path='/tmp/output.mp4',
            start_time=0.0,
            duration=10.0
        )
        self.queue.add_task(task)
        self.queue.get_next_task('worker_1')
        self.queue.mark_completed('test_1')
        
        completed_task = self.queue.get_task('test_1')
        self.assertEqual(completed_task.status, TaskStatus.COMPLETED)
    
    def test_statistics(self):
        """Test queue statistics"""
        for i in range(5):
            task = Task(
                task_id=f'test_{i}',
                segment_id=i,
                input_path='/tmp/input.mp4',
                output_path=f'/tmp/output_{i}.mp4',
                start_time=i * 10.0,
                duration=10.0
            )
            self.queue.add_task(task)
        
        stats = self.queue.get_statistics()
        self.assertEqual(stats['total'], 5)
        self.assertEqual(stats['pending'], 5)


class TestVideoSegmenter(unittest.TestCase):
    """Test video segmentation"""
    
    def test_check_ffmpeg(self):
        """Test FFmpeg availability"""
        processor = VideoProcessor()
        has_ffmpeg = processor.check_ffmpeg()
        # This may fail if FFmpeg is not installed, which is expected
        self.assertIsInstance(has_ffmpeg, bool)


if __name__ == '__main__':
    unittest.main()
