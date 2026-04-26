import subprocess
import os

def process_chunk(input_chunk, output_chunk):
    os.makedirs(os.path.dirname(output_chunk), exist_ok=True)

    cmd = [
        "ffmpeg", "-y",
        "-i", input_chunk,
        "-vf", "scale=640:360",
        output_chunk
    ]

    subprocess.run(cmd, check=True)
