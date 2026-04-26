import csv
import os
import subprocess
import time

INPUTS = [
    ("24s", "input/test_24sec.mp4"),
    ("120s", "input/test_120sec.mp4"),
    ("full", "input/finalecc-testvid.mp4"),
]

STRATEGIES = ["single", "static", "dynamic"]

RESULTS_FILE = "benchmark_results.csv"


def clean():
    subprocess.run("rm -rf chunks processed output file_list.txt", shell=True)


def run_command(input_label, input_file, strategy):
    output_file = f"output/{input_label}_{strategy}.mp4"

    cmd = [
        "python3", "src/main.py",
        "--input", input_file,
        "--output", output_file,
        "--strategy", strategy
    ]

    env = os.environ.copy()
    env["PYTHONPATH"] = "src"

    start = time.time()
    subprocess.run(cmd, check=True, env=env)
    end = time.time()

    return round(end - start, 2), output_file


def main():
    rows = []

    for input_label, input_file in INPUTS:
        for strategy in STRATEGIES:
            print(f"\nRunning {strategy} on {input_label}...")
            clean()

            runtime, output_file = run_command(input_label, input_file, strategy)

            rows.append({
                "input_size": input_label,
                "strategy": strategy,
                "runtime_seconds": runtime,
                "output_file": output_file
            })

            print(f"{input_label} | {strategy} | {runtime} sec")

    with open(RESULTS_FILE, "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["input_size", "strategy", "runtime_seconds", "output_file"]
        )
        writer.writeheader()
        writer.writerows(rows)
import csv
import os
import subprocess
import time

INPUTS = [
    ("24s", "input/test_24sec.mp4"),
    ("120s", "input/test_120sec.mp4"),
    ("full", "input/finalecc-testvid.mp4"),
]

STRATEGIES = ["single", "static", "dynamic"]

RESULTS_FILE = "benchmark_results.csv"


def clean():
    subprocess.run("rm -rf chunks processed output file_list.txt", shell=True)


def run_command(input_label, input_file, strategy):
    output_file = f"output/{input_label}_{strategy}.mp4"

    cmd = [
        "python3", "src/main.py",
        "--input", input_file,
        "--output", output_file,
        "--strategy", strategy
    ]

    env = os.environ.copy()
    env["PYTHONPATH"] = "src"

    start = time.time()
    subprocess.run(cmd, check=True, env=env)
    end = time.time()

    return round(end - start, 2), output_file


def main():
    rows = []

    for input_label, input_file in INPUTS:
        for strategy in STRATEGIES:
            print(f"\nRunning {strategy} on {input_label}...")
            clean()

            runtime, output_file = run_command(input_label, input_file, strategy)

            rows.append({
                "input_size": input_label,
                "strategy": strategy,
                "runtime_seconds": runtime,
                "output_file": output_file
            })

            print(f"{input_label} | {strategy} | {runtime} sec")

    with open(RESULTS_FILE, "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["input_size", "strategy", "runtime_seconds", "output_file"]
        )
        writer.writeheader()
        writer.writerows(rows)
        writer.writerows(rows)

    print("\nBenchmark complete.")
    print(f"Results saved to {RESULTS_FILE}")


if __name__ == "__main__":
    main()
