import os
import subprocess

def split_video(input_file, output_dir, chunk_duration=10):
    os.makedirs(output_dir, exist_ok=True)

    cmd = [
        "ffmpeg", "-y",
        "-i", input_file,
        "-c", "copy",
        "-map", "0",
        "-segment_time", str(chunk_duration),
        "-f", "segment",
        f"{output_dir}/chunk_%03d.mp4"
    ]

    subprocess.run(cmd, check=True)

    chunks = sorted([
        os.path.join(output_dir, f)
        for f in os.listdir(output_dir)
        if f.endswith(".mp4")
    ])

    return chunks
