import os
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed

WORKERS = ["ecc-edvid-worker1", "ecc-edvid-worker2"]
#WORKERS = ["fake-worker", "ecc-edvid-worker2"]
MAX_RETRIES = 2


def run_on_worker(worker, chunk_path, index):
    remote_input = f"~/final_project/framework/chunk_{index:03d}.mp4"
    remote_output = f"~/final_project/framework/out_{index:03d}.mp4"
    local_output = f"processed/out_{index:03d}.mp4"

    os.makedirs("processed", exist_ok=True)

    subprocess.run(["scp", chunk_path, f"ubuntu@{worker}:{remote_input}"], check=True)

    subprocess.run([
        "ssh", f"ubuntu@{worker}",
        f'ffmpeg -y -i {remote_input} -vf "scale=640:360" {remote_output}'
    ], check=True)

    subprocess.run(["scp", f"ubuntu@{worker}:{remote_output}", local_output], check=True)

    return local_output


def run_with_retry(chunk_path, index):
    last_error = None

    for attempt in range(MAX_RETRIES + 1):
        worker = WORKERS[(index + attempt) % len(WORKERS)]

        try:
            print(f"Processing chunk {index} on {worker}, attempt {attempt + 1}")
            return run_on_worker(worker, chunk_path, index)

        except subprocess.CalledProcessError as e:
            print(f"Worker {worker} failed for chunk {index}. Retrying...")
            last_error = e

    raise RuntimeError(f"Chunk {index} failed after {MAX_RETRIES + 1} attempts") from last_error


def process_dynamic(chunks):
    processed = []

    with ThreadPoolExecutor(max_workers=len(WORKERS)) as executor:
        futures = []

        for i, chunk in enumerate(chunks):
            futures.append(executor.submit(run_with_retry, chunk, i))

        for future in as_completed(futures):
            processed.append(future.result())

    return sorted(processed)
