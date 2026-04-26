"""
Video segmentation using FFmpeg
Writes segments to NFS-shared directory
"""

import subprocess
import os
import json
from pathlib import Path


class VideoSegmenter:
    """Segments video into chunks using FFmpeg"""
    
    def __init__(self, segment_duration=5):
        """
        Args:
            segment_duration: Duration of each segment in seconds
        """
        self.segment_duration = segment_duration
    
    def get_video_info(self, video_path):
        """Get video metadata using ffprobe"""
        cmd = [
            'ffprobe',
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            '-show_streams',
            video_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"Failed to get video info: {result.stderr}")
        
        data = json.loads(result.stdout)
        duration = float(data['format']['duration'])
        
        return {'duration': duration}
    
    def create_segments(self, video_path, output_dir):
        """
        Segment video into chunks and write to NFS directory
        
        Args:
            video_path: Input video path
            output_dir: NFS-shared output directory (e.g., /home/ubuntu/nfs_shared/chunks)
            
        Returns:
            List of segment filenames
        """
        os.makedirs(output_dir, exist_ok=True)
        
        # Get video duration
        info = self.get_video_info(video_path)
        duration = info['duration']
        num_segments = int(duration / self.segment_duration)
        if duration % self.segment_duration > 0:
            num_segments += 1
        
        segments = []
        
        for i in range(num_segments):
            start_time = i * self.segment_duration
            # Calculate actual duration for this segment
            remaining_duration = duration - start_time
            actual_duration = min(self.segment_duration, remaining_duration)
            
            segment_name = f"chunk_{i:03d}.mp4"
            output_path = os.path.join(output_dir, segment_name)
            
            # Extract segment using FFmpeg (re-encode for accuracy)
            cmd = [
                'ffmpeg',
                '-i', video_path,
                '-ss', str(start_time),
                '-t', str(actual_duration),
                '-c:v', 'libx264',
                '-preset', 'ultrafast',  # Fast encoding for segmentation
                '-crf', '23',
                '-avoid_negative_ts', '1',
                '-y',
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                raise RuntimeError(f"Segmentation failed: {result.stderr}")
            
            segments.append(segment_name)
            print(f"Created segment {i+1}/{num_segments}: {segment_name}")
        
        return segments
