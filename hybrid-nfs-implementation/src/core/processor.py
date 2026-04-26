"""
FFmpeg video processing utilities
"""

import subprocess


class VideoProcessor:
    """Handles FFmpeg video processing operations"""
    
    @staticmethod
    def check_ffmpeg():
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
    
    @staticmethod
    def build_ffmpeg_command(input_path, output_path, codec='libx264', 
                            bitrate='2M', preset='medium'):
        """
        Build FFmpeg processing command
        
        Args:
            input_path: Input video path (NFS path)
            output_path: Output video path (NFS path)
            codec: Video codec
            bitrate: Video bitrate
            preset: Encoding preset
            
        Returns:
            FFmpeg command as string
        """
        cmd = (
            f"ffmpeg -i {input_path} "
            f"-c:v {codec} "
            f"-b:v {bitrate} "
            f"-preset {preset} "
            f"-y {output_path}"
        )
        return cmd
