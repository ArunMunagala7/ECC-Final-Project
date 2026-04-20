"""
Video merger module
Handles combining processed segments into final output
"""

import os
import subprocess
from typing import List
from .logger import LoggerMixin
from .segmenter import VideoSegment


class VideoMerger(LoggerMixin):
    """Handles merging video segments using FFmpeg"""
    
    def merge_segments(
        self,
        segments: List[VideoSegment],
        output_path: str,
        cleanup: bool = True
    ) -> str:
        """
        Merge processed video segments into final output
        
        Args:
            segments: List of VideoSegment objects (in order)
            output_path: Path for final merged video
            cleanup: Whether to delete segment files after merging
            
        Returns:
            Path to merged video file
        """
        # Sort segments by ID to ensure correct order
        sorted_segments = sorted(segments, key=lambda s: s.segment_id)
        
        # Create concat file for FFmpeg
        concat_file = output_path + '.concat.txt'
        
        try:
            with open(concat_file, 'w') as f:
                for segment in sorted_segments:
                    # Use processed output path
                    segment_file = segment.output_path
                    if os.path.exists(segment_file):
                        # FFmpeg concat requires relative or absolute paths with proper escaping
                        abs_path = os.path.abspath(segment_file)
                        f.write(f"file '{abs_path}'\n")
                    else:
                        self.logger.warning(f"Segment file not found: {segment_file}")
            
            self.logger.info(f"Merging {len(sorted_segments)} segments...")
            
            # Use FFmpeg concat demuxer for lossless merging
            cmd = [
                'ffmpeg',
                '-f', 'concat',
                '-safe', '0',
                '-i', concat_file,
                '-c', 'copy',  # Copy streams without re-encoding
                '-y',  # Overwrite output
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                self.logger.error(f"FFmpeg merge failed: {result.stderr}")
                raise RuntimeError(f"Failed to merge segments: {result.stderr}")
            
            self.logger.info(f"Successfully merged video to: {output_path}")
            
            # Cleanup
            if cleanup:
                self._cleanup_files([concat_file])
            
            return output_path
            
        except Exception as e:
            self.logger.error(f"Error during merge: {e}")
            raise
        finally:
            # Always cleanup concat file
            if os.path.exists(concat_file):
                os.remove(concat_file)
    
    def _cleanup_files(self, file_paths: List[str]):
        """Remove temporary files"""
        for path in file_paths:
            try:
                if os.path.exists(path):
                    os.remove(path)
                    self.logger.debug(f"Removed: {path}")
            except Exception as e:
                self.logger.warning(f"Failed to remove {path}: {e}")
