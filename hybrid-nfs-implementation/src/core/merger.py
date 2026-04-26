"""
Video merging using FFmpeg concat
Reads processed segments from NFS-shared directory
"""

import subprocess
import os
from pathlib import Path


class VideoMerger:
    """Merges processed video segments using FFmpeg"""
    
    def merge_segments(self, input_dir, output_path):
        """
        Merge processed segments from NFS directory into final video
        
        Args:
            input_dir: NFS-shared directory with processed segments
            output_path: Final output video path
        """
        # Get all processed files and sort
        processed_files = sorted([
            f for f in os.listdir(input_dir) 
            if f.endswith('.mp4')
        ])
        
        if not processed_files:
            raise RuntimeError(f"No processed segments found in {input_dir}")
        
        # Create concat file
        concat_file = os.path.join(input_dir, 'concat_list.txt')
        
        with open(concat_file, 'w') as f:
            for filename in processed_files:
                file_path = os.path.join(input_dir, filename)
                # FFmpeg concat requires proper path format
                f.write(f"file '{file_path}'\n")
        
        # Use FFmpeg concat demuxer
        cmd = [
            'ffmpeg',
            '-f', 'concat',
            '-safe', '0',
            '-i', concat_file,
            '-c', 'copy',  # Lossless merge
            '-y',
            output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise RuntimeError(f"Merge failed: {result.stderr}")
        
        # Cleanup concat file
        os.remove(concat_file)
        
        print(f"Merged {len(processed_files)} segments into {output_path}")
        
        return output_path
