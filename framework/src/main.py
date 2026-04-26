import argparse
import os
import time

from core.static_processor import process_static
from core.segmenter import split_video
from core.processor import process_chunk
from core.merger import merge_chunks
from core.dynamic_processor import process_dynamic


def run_single(input_video, output_file):
    print("Running single-node baseline...")
    start = time.time()

    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    process_chunk(input_video, output_file)

    end = time.time()
    print(f"Single-node runtime: {end - start:.2f} seconds")


def run_dynamic(input_video, output_file):
    print("Running dynamic distributed pipeline...")
    start = time.time()

    chunk_dir = "chunks"
    processed_dir = "processed"

    chunks = split_video(input_video, chunk_dir)
    processed_chunks = process_dynamic(chunks)
    merge_chunks(processed_chunks, output_file)

    end = time.time()
    print(f"Dynamic distributed runtime: {end - start:.2f} seconds")


def run_static(input_video, output_file):
    print("Running static distributed pipeline...")
    start = time.time()

    chunk_dir = "chunks"
    chunks = split_video(input_video, chunk_dir)
    processed_chunks = process_static(chunks)
    merge_chunks(processed_chunks, output_file)

    end = time.time()
    print(f"Static distributed runtime: {end - start:.2f} seconds")


def main():
    parser = argparse.ArgumentParser(description="Elastic Distributed Video Processing Framework")

    parser.add_argument("--input", required=True, help="Path to input video")
    parser.add_argument("--output", required=True, help="Path to output video")
    parser.add_argument(
        "--strategy",
        choices=["single", "static", "dynamic"],
        default="dynamic",
        help="Processing strategy"
    )

    args = parser.parse_args()

    if args.strategy == "single":
        run_single(args.input, args.output)
    elif args.strategy == "static":
        run_static(args.input, args.output)
    elif args.strategy == "dynamic":
        run_dynamic(args.input, args.output)


if __name__ == "__main__":
    main()
