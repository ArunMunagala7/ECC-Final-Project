"""
Remote worker implementation using SSH + NFS
"""

import subprocess
import time
from ..core.processor import VideoProcessor


class RemoteWorker:
    """
    Worker that executes FFmpeg on remote VM via SSH
    Uses NFS paths (no file transfer needed)
    """
    
    def __init__(self, worker_id, ssh_host, ssh_user="ubuntu", ssh_key=None):
        """
        Args:
            worker_id: Unique worker identifier
            ssh_host: SSH hostname or IP
            ssh_user: SSH username
            ssh_key: Path to SSH private key (optional)
        """
        self.worker_id = worker_id
        self.ssh_host = ssh_host
        self.ssh_user = ssh_user
        self.ssh_key = ssh_key
        self.status = 'idle'
        self.tasks_completed = 0
        self.tasks_failed = 0
        self.is_healthy = True
    
    def process_task(self, task):
        """
        Execute FFmpeg on remote worker using NFS paths
        
        Args:
            task: Dict with 'input_path' and 'output_path' (both NFS paths)
            
        Returns:
            Dict with 'success', 'output_path', 'duration'
        """
        self.status = 'processing'
        start_time = time.time()
        
        input_path = task['input_path']
        output_path = task['output_path']
        
        # Build FFmpeg command
        ffmpeg_cmd = VideoProcessor.build_ffmpeg_command(
            input_path, 
            output_path,
            codec=task.get('codec', 'libx264'),
            bitrate=task.get('bitrate', '2M'),
            preset=task.get('preset', 'medium')
        )
        
        # Build SSH command
        ssh_cmd = self._build_ssh_command(ffmpeg_cmd)
        
        try:
            # Execute on remote worker
            result = subprocess.run(
                ssh_cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            duration = time.time() - start_time
            
            if result.returncode == 0:
                self.tasks_completed += 1
                self.status = 'idle'
                return {
                    'success': True,
                    'output_path': output_path,
                    'duration': duration,
                    'worker_id': self.worker_id
                }
            else:
                self.tasks_failed += 1
                self.status = 'idle'
                return {
                    'success': False,
                    'error': result.stderr,
                    'duration': duration,
                    'worker_id': self.worker_id
                }
        
        except subprocess.TimeoutExpired:
            self.tasks_failed += 1
            self.status = 'idle'
            return {
                'success': False,
                'error': 'Task timeout',
                'worker_id': self.worker_id
            }
        
        except Exception as e:
            self.tasks_failed += 1
            self.status = 'idle'
            return {
                'success': False,
                'error': str(e),
                'worker_id': self.worker_id
            }
    
    def _build_ssh_command(self, remote_command):
        """Build SSH command string"""
        ssh_cmd = f"ssh "
        
        if self.ssh_key:
            ssh_cmd += f"-i {self.ssh_key} "
        
        ssh_cmd += f"-o StrictHostKeyChecking=no "
        ssh_cmd += f"{self.ssh_user}@{self.ssh_host} "
        ssh_cmd += f"'{remote_command}'"
        
        return ssh_cmd
    
    def check_health(self, timeout=5):
        """
        Check if worker is reachable via SSH
        
        Args:
            timeout: SSH connection timeout in seconds
            
        Returns:
            bool: True if worker is healthy, False otherwise
        """
        try:
            # Simple SSH echo command to test connectivity
            ssh_cmd = f"ssh "
            
            if self.ssh_key:
                ssh_cmd += f"-i {self.ssh_key} "
            
            ssh_cmd += f"-o StrictHostKeyChecking=no "
            ssh_cmd += f"-o ConnectTimeout={timeout} "
            ssh_cmd += f"{self.ssh_user}@{self.ssh_host} "
            ssh_cmd += "'echo healthy'"
            
            result = subprocess.run(
                ssh_cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout + 1
            )
            
            self.is_healthy = (result.returncode == 0 and 'healthy' in result.stdout)
            return self.is_healthy
            
        except Exception as e:
            print(f"  ⚠️  Worker {self.worker_id} health check failed: {str(e)}")
            self.is_healthy = False
            return False
    
    def get_status(self):
        """Get worker status"""
        return {
            'worker_id': self.worker_id,
            'status': self.status,
            'tasks_completed': self.tasks_completed,
            'tasks_failed': self.tasks_failed,
            'ssh_host': self.ssh_host,
            'is_healthy': self.is_healthy
        }


class LocalWorker:
    """
    Local worker for testing without Jetstream
    Simulates remote execution but runs FFmpeg locally
    """
    
    def __init__(self, worker_id):
        self.worker_id = worker_id
        self.status = 'idle'
        self.tasks_completed = 0
        self.tasks_failed = 0
        self.is_healthy = True
    
    def check_health(self, timeout=5):
        """Local workers are always healthy"""
        self.is_healthy = True
        return True
    
    def process_task(self, task):
        """Process task locally (for testing)"""
        import os
        self.status = 'processing'
        start_time = time.time()
        
        input_path = task['input_path']
        output_path = task['output_path']
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Build FFmpeg command as list
        cmd = [
            'ffmpeg',
            '-i', input_path,
            '-c:v', task.get('codec', 'libx264'),
            '-b:v', task.get('bitrate', '2M'),
            '-preset', task.get('preset', 'medium'),
            '-y',
            output_path
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            duration = time.time() - start_time
            
            if result.returncode == 0:
                self.tasks_completed += 1
                self.status = 'idle'
                return {
                    'success': True,
                    'output_path': output_path,
                    'duration': duration,
                    'worker_id': self.worker_id
                }
            else:
                self.tasks_failed += 1
                self.status = 'idle'
                return {
                    'success': False,
                    'error': result.stderr,
                    'duration': duration,
                    'worker_id': self.worker_id
                }
        
        except Exception as e:
            self.tasks_failed += 1
            self.status = 'idle'
            return {
                'success': False,
                'error': str(e),
                'worker_id': self.worker_id
            }
    
    def get_status(self):
        """Get worker status"""
        return {
            'worker_id': self.worker_id,
            'status': self.status,
            'tasks_completed': self.tasks_completed,
            'tasks_failed': self.tasks_failed,
            'ssh_host': 'localhost',
            'is_healthy': self.is_healthy
        }
