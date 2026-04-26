import os
import subprocess

WORKERS = ["10.4.36.67", "10.4.36.101"]


def process_static(chunks):
    processed = []
    os.makedirs("processed", exist_ok=True)

    for i, chunk in enumerate(chunks):
        worker = WORKERS[i % len(WORKERS)]

        remote_input = f"~/final_project/framework/static_chunk_{i:03d}.mp4"
        remote_output = f"~/final_project/framework/static_out_{i:03d}.mp4"
        local_output = f"processed/static_out_{i:03d}.mp4"

        print(f"Assigning {chunk} to {worker}")

        subprocess.run(["scp", chunk, f"ubuntu@{worker}:{remote_input}"], check=True)

        subprocess.run([
            "ssh", f"ubuntu@{worker}",
            f'ffmpeg -y -i {remote_input} -vf "scale=640:360" {remote_output}'
        ], check=True)

        subprocess.run(["scp", f"ubuntu@{worker}:{remote_output}", local_output], check=True)

        processed.append(local_output)

    return processed
