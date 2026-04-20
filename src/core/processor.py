"""
Video processor module
Handles FFmpeg video processing operations
"""

import os
import subprocess
from typing import Dict, Optional
from .logger import LoggerMixin


class VideoProcessor(LoggerMixin):
    """Handles video processing using FFmpeg"""
    
    def __init__(
        self,
        codec: str = 'libx264',
        crf: int = 23,
        preset: str = 'medium',
        scale: Optional[str] = None,
        bitrate: Optional[str] = None
    ):
        """
        Initialize video processor
        
        Args:
            codec: Video codec (e.g., libx264, libx265)
            crf: Constant Rate Factor (0-51, lower is better quality)
            preset: Encoding preset (ultrafast to veryslow)
            scale: Resolution (e.g., "1280:720" or None for original)
            bitrate: Target bitrate (e.g., "2M" or None for auto)
        """
        self.codec = codec
        self.crf = crf
        self.preset = preset
        self.scale = scale
        self.bitrate = bitrate
    
    def process_segment(
        self,
        input_path: str,
        output_path: str,
        start_time: Optional[float] = None,
        duration: Optional[float] = None
    ) -> str:
        """
        Process a video segment
        
        Args:
            input_path: Path to input video
            output_path: Path for processed output
            start_time: Start time in seconds (optional, for extraction)
            duration: Duration in seconds (optional, for extraction)
            
        Returns:
            Path to processed video
        """
        # Build FFmpeg command
        cmd = ['ffmpeg']
        
        # Input file
        if start_time is not None:
            cmd.extend(['-ss', str(start_time)])
        
        cmd.extend(['-i', input_path])
        
        if duration is not None:
            cmd.extend(['-t', str(duration)])
        
        # Video codec and quality
        cmd.extend(['-c:v', self.codec])
        cmd.extend(['-crf', str(self.crf)])
        cmd.extend(['-preset', self.preset])
        
        # Scaling if specified
        if self.scale:
            cmd.extend(['-vf', f'scale={self.scale}'])
        
        # Bitrate if specified
        if self.bitrate:
            cmd.extend(['-b:v', self.bitrate])
        
        # Audio codec (copy for speed)
        cmd.extend(['-c:a', 'aac'])
        cmd.extend(['-b:a', '128k'])
        
        # Output file
        cmd.extend(['-y', output_path])
        
        try:
            self.logger.debug(f"Processing: {input_path} -> {output_path}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            self.logger.info(f"Successfully processed: {output_path}")
            return output_path
            
        except subprocess.CalledProcessError as e:
            error_msg = f"FFmpeg processing failed: {e.stderr}"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)
    
    def process_with_filter(
        self,
        input_path: str,
        output_path: str,
        filter_complex: str
    ) -> str:
        """
        Process video with custom FFmpeg filter
        
        Args:
            input_path: Path to input video
            output_path: Path for processed output
            filter_complex: FFmpeg filter expression
            
        Returns:
            Path to processed video
        """
        cmd = [
            'ffmpeg',
            '-i', input_path,
            '-filter_complex', filter_complex,
            '-c:v', self.codec,
            '-crf', str(self.crf),
            '-preset', self.preset,
            '-c:a', 'aac',
            '-y', output_path
        ]
        
        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True)
            self.logger.info(f"Processed with filter: {output_path}")
            return output_path
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Filter processing failed: {e.stderr}")
            raise
    
    @staticmethod
    def check_ffmpeg() -> bool:
        """Check if FFmpeg is installed"""
        try:
            subprocess.run(
                ['ffmpeg', '-version'],
                capture_output=True,
                check=True
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
