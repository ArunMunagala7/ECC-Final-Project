"""
Master coordinator for distributed video processing
Supports static and dynamic scheduling with NFS + SSH workers
"""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from ..core.segmenter import VideoSegmenter
from ..core.merger import VideoMerger
from ..worker import RemoteWorker, LocalWorker


class Master:
    """
    Master coordinator that orchestrates video processing across workers
    Uses NFS for shared storage and SSH for remote execution
    """
    
    def __init__(self, config):
        """
        Args:
            config: Dict with configuration (NFS paths, workers, etc.)
        """
        self.config = config
        self.segmenter = VideoSegmenter(
            segment_duration=config.get('segment_duration', 5)
        )
        self.merger = VideoMerger()
    
    def process_static(self, video_path, workers):
        """
        Static scheduling: Fixed assignment of chunks to workers
        Chunk i → Worker (i % num_workers)
        
        Args:
            video_path: Input video path
            workers: List of worker instances (RemoteWorker or LocalWorker)
            
        Returns:
            Dict with processing statistics
        """
        start_time = time.time()
        
        nfs_base = self.config.get('nfs_base_dir', '/tmp/video_processing')
        chunk_dir = f"{nfs_base}/chunks"
        processed_dir = f"{nfs_base}/processed"
        output_dir = f"{nfs_base}/output"
        
        # Ensure all directories exist
        import os
        os.makedirs(chunk_dir, exist_ok=True)
        os.makedirs(processed_dir, exist_ok=True)
        os.makedirs(output_dir, exist_ok=True)
        
        print(f"\n=== Dynamic Scheduling with {len(workers)} workers ===")
        
        # Step 1: Segment video into NFS directory
        print(f"Segmenting video into {chunk_dir}...")
        segments = self.segmenter.create_segments(video_path, chunk_dir)
        num_segments = len(segments)
        print(f"Created {num_segments} segments")
        
        # Step 2: Static assignment - chunk i goes to worker (i % num_workers)
        print(f"\nAssigning chunks to workers (static round-robin)...")
        tasks = []
        for i, segment in enumerate(segments):
            worker_idx = i % len(workers)
            task = {
                'id': i,
                'input_path': f"{chunk_dir}/{segment}",
                'output_path': f"{processed_dir}/out_{i:03d}.mp4",
                'worker_id': worker_idx,
                'codec': self.config.get('codec', 'libx264'),
                'bitrate': self.config.get('bitrate', '2M'),
                'preset': self.config.get('preset', 'medium')
            }
            tasks.append(task)
            print(f"  Chunk {i} → Worker {worker_idx}")
        
        # Step 3: Process tasks in parallel using thread pool
        print(f"\nProcessing {num_segments} chunks...")
        results = []
        
        with ThreadPoolExecutor(max_workers=len(workers)) as executor:
            futures = []
            
            for task in tasks:
                worker = workers[task['worker_id']]
                future = executor.submit(worker.process_task, task)
                futures.append((future, task))
            
            # Collect results as they complete
            completed = 0
            for future, task in futures:
                result = future.result()
                results.append(result)
                completed += 1
                
                status = "✓" if result['success'] else "✗"
                duration = result.get('duration', 0)
                print(f"  [{completed}/{num_segments}] {status} Chunk {task['id']} "
                      f"(Worker {result['worker_id']}, {duration:.2f}s)")
        
        # Step 4: Merge processed segments
        print(f"\nMerging processed segments...")
        output_path = f"{output_dir}/final_static.mp4"
        self.merger.merge_segments(processed_dir, output_path)
        
        total_time = time.time() - start_time
        successful = sum(1 for r in results if r['success'])
        failed = num_segments - successful
        
        # Calculate statistics
        stats = {
            'strategy': 'static',
            'num_workers': len(workers),
            'num_segments': num_segments,
            'successful': successful,
            'failed': failed,
            'total_time': total_time,
            'output_path': output_path,
            'worker_stats': [w.get_status() for w in workers]
        }
        
        print(f"\n=== Static Processing Complete ===")
        print(f"Total time: {total_time:.2f}s")
        print(f"Successful: {successful}/{num_segments}")
        print(f"Output: {output_path}")
        
        return stats
    
    def process_dynamic(self, video_path, workers, max_retries=2):
        """
        Dynamic scheduling: Task queue with work stealing
        Workers pull next available chunk from shared queue
        
        Args:
            video_path: Input video path
            workers: List of worker instances
            max_retries: Max retry attempts for failed tasks
            
        Returns:
            Dict with processing statistics
        """
        start_time = time.time()
        
        nfs_base = self.config.get('nfs_base_dir', '/tmp/video_processing')
        chunk_dir = f"{nfs_base}/chunks"
        processed_dir = f"{nfs_base}/processed"
        output_dir = f"{nfs_base}/output"
        
        # Ensure all directories exist
        import os
        os.makedirs(chunk_dir, exist_ok=True)
        os.makedirs(processed_dir, exist_ok=True)
        os.makedirs(output_dir, exist_ok=True)
        
        # Step 1: Segment video
        print(f"Segmenting video into {chunk_dir}...")
        segments = self.segmenter.create_segments(video_path, chunk_dir)
        num_segments = len(segments)
        print(f"Created {num_segments} segments")
        
        # Step 2: Create task queue
        print(f"\nCreating task queue...")
        task_queue = []
        for i, segment in enumerate(segments):
            task = {
                'id': i,
                'input_path': f"{chunk_dir}/{segment}",
                'output_path': f"{processed_dir}/out_{i:03d}.mp4",
                'codec': self.config.get('codec', 'libx264'),
                'bitrate': self.config.get('bitrate', '2M'),
                'preset': self.config.get('preset', 'medium'),
                'retry_count': 0
            }
            task_queue.append(task)
        
        # Shared state for task queue (thread-safe through GIL for simple operations)
        from threading import Lock
        queue_lock = Lock()
        completed_tasks = []
        failed_tasks = []
        
        def worker_thread(worker):
            """Each thread pulls tasks and executes on assigned worker"""
            while True:
                # Get next task from queue
                task = None
                with queue_lock:
                    if task_queue:
                        task = task_queue.pop(0)
                
                if task is None:
                    break  # No more tasks
                
                # Process task on remote worker
                result = worker.process_task(task)
                
                # Handle result
                with queue_lock:
                    if result['success']:
                        completed_tasks.append((task, result))
                        print(f"  ✓ Chunk {task['id']} completed by Worker {result['worker_id']} "
                              f"({result['duration']:.2f}s)")
                    else:
                        # Retry logic
                        if task['retry_count'] < max_retries:
                            task['retry_count'] += 1
                            task_queue.append(task)  # Re-add to queue
                            print(f"  ⟳ Chunk {task['id']} failed, retrying "
                                  f"(attempt {task['retry_count']}/{max_retries})")
                        else:
                            failed_tasks.append((task, result))
                            print(f"  ✗ Chunk {task['id']} failed permanently "
                                  f"(Worker {result['worker_id']})")
        
        # Step 3: Start worker threads
        print(f"\nProcessing {num_segments} chunks dynamically...")
        with ThreadPoolExecutor(max_workers=len(workers)) as executor:
            futures = [executor.submit(worker_thread, w) for w in workers]
            
            # Wait for all threads to complete
            for future in futures:
                future.result()
        
        # Step 4: Merge processed segments
        print(f"\nMerging processed segments...")
        output_path = f"{output_dir}/final_dynamic.mp4"
        self.merger.merge_segments(processed_dir, output_path)
        
        total_time = time.time() - start_time
        successful = len(completed_tasks)
        failed = len(failed_tasks)
        
        # Calculate statistics
        stats = {
            'strategy': 'dynamic',
            'num_workers': len(workers),
            'num_segments': num_segments,
            'successful': successful,
            'failed': failed,
            'total_time': total_time,
            'output_path': output_path,
            'worker_stats': [w.get_status() for w in workers]
        }
        
        print(f"\n=== Dynamic Processing Complete ===")
        print(f"Total time: {total_time:.2f}s")
        print(f"Successful: {successful}/{num_segments}")
        print(f"Output: {output_path}")
        
        return stats
