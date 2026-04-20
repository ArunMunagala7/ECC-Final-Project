"""
Video segmentation module
Handles splitting videos into processable chunks
"""

import os
import json
import subprocess
from typing import List, Dict, Tuple
from dataclasses import dataclass
from .logger import LoggerMixin


@dataclass
class VideoSegment:
    """Represents a video segment"""
    segment_id: int
    start_time: float
    duration: float
    input_path: str
    output_path: str
    
    def to_dict(self) -> Dict:
        return {
            'segment_id': self.segment_id,
            'start_time': self.start_time,
            'duration': self.duration,
            'input_path': self.input_path,
            'output_path': self.output_path
        }


class VideoSegmenter(LoggerMixin):
    """Handles video segmentation using FFmpeg"""
    
    def __init__(self, chunk_duration: float = 10.0):
        """
        Initialize video segmenter
        
        Args:
            chunk_duration: Duration of each chunk in seconds
        """
        self.chunk_duration = chunk_duration
    
    def get_video_info(self, video_path: str) -> Dict:
        """
        Get video metadata using FFprobe
        
        Args:
            video_path: Path to video file
            
        Returns:
            Dictionary containing video metadata
        """
        cmd = [
            'ffprobe',
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            '-show_streams',
            video_path
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            info = json.loads(result.stdout)
            
            # Extract relevant information
            format_info = info.get('format', {})
            video_stream = next(
                (s for s in info.get('streams', []) if s['codec_type'] == 'video'),
                {}
            )
            
            return {
                'duration': float(format_info.get('duration', 0)),
                'size': int(format_info.get('size', 0)),
                'bit_rate': int(format_info.get('bit_rate', 0)),
                'width': video_stream.get('width', 0),
                'height': video_stream.get('height', 0),
                'codec': video_stream.get('codec_name', 'unknown'),
                'fps': eval(video_stream.get('r_frame_rate', '0/1'))
            }
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to get video info: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Error parsing video info: {e}")
            raise
    
    def create_segments(
        self,
        video_path: str,
        output_dir: str,
        num_segments: int = None
    ) -> List[VideoSegment]:
        """
        Create video segment metadata without actually splitting the file
        
        Args:
            video_path: Path to input video
            output_dir: Directory to store segment metadata
            num_segments: Number of segments to create (if None, uses chunk_duration)
            
        Returns:
            List of VideoSegment objects
        """
        os.makedirs(output_dir, exist_ok=True)
        
        # Get video duration
        info = self.get_video_info(video_path)
        total_duration = info['duration']
        
        self.logger.info(f"Video duration: {total_duration:.2f}s")
        
        # Calculate segments
        if num_segments:
            chunk_duration = total_duration / num_segments
        else:
            chunk_duration = self.chunk_duration
        
        segments = []
        segment_id = 0
        current_time = 0.0
        
        while current_time < total_duration:
            remaining = total_duration - current_time
            duration = min(chunk_duration, remaining)
            
            segment = VideoSegment(
                segment_id=segment_id,
                start_time=current_time,
                duration=duration,
                input_path=video_path,
                output_path=os.path.join(output_dir, f"segment_{segment_id:04d}.mp4")
            )
            
            segments.append(segment)
            current_time += duration
            segment_id += 1
        
        self.logger.info(f"Created {len(segments)} segment definitions")
        
        # Save segment metadata
        metadata_path = os.path.join(output_dir, 'segments.json')
        with open(metadata_path, 'w') as f:
            json.dump([s.to_dict() for s in segments], f, indent=2)
        
        return segments
    
    def extract_segment(self, segment: VideoSegment) -> str:
        """
        Extract a specific segment from the video
        
        Args:
            segment: VideoSegment object
            
        Returns:
            Path to extracted segment
        """
        cmd = [
            'ffmpeg',
            '-i', segment.input_path,
            '-ss', str(segment.start_time),
            '-t', str(segment.duration),
            '-c', 'copy',  # Copy without re-encoding for speed
            '-avoid_negative_ts', '1',
            '-y',  # Overwrite output file
            segment.output_path
        ]
        
        try:
            self.logger.debug(f"Extracting segment {segment.segment_id}")
            subprocess.run(cmd, capture_output=True, check=True)
            self.logger.info(f"Segment {segment.segment_id} extracted successfully")
            return segment.output_path
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to extract segment {segment.segment_id}: {e.stderr}")
            raise
    
    @staticmethod
    def load_segments(metadata_path: str) -> List[VideoSegment]:
        """
        Load segment metadata from JSON file
        
        Args:
            metadata_path: Path to segments.json file
            
        Returns:
            List of VideoSegment objects
        """
        with open(metadata_path, 'r') as f:
            data = json.load(f)
        
        return [VideoSegment(**item) for item in data]
