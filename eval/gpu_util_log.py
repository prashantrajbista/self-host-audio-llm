"""Phase 5: GPU utilization logger — polls nvidia-smi during a load test, CSV out.
Run alongside eval.latency_bench (separate terminal) to correlate load with GPU usage.

Run: python -m eval.gpu_util_log --duration 60 --out eval/results/gpu_util.csv
"""

import argparse
import shutil
import subprocess
import sys
import time


def main(duration: int, out_path: str):
    if not shutil.which("nvidia-smi"):
        sys.exit("nvidia-smi not found — this must run on a machine with an NVIDIA GPU.")

    proc = subprocess.Popen(
        [
            "nvidia-smi",
            "--query-gpu=timestamp,utilization.gpu,memory.used,memory.total",
            "--format=csv",
            "-l",
            "1",
            "-f",
            out_path,
        ]
    )
    print(f"logging GPU utilization to {out_path} for {duration}s...")
    time.sleep(duration)
    proc.terminate()
    print("done")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--duration", type=int, default=60)
    parser.add_argument("--out", default="eval/results/gpu_util.csv")
    args = parser.parse_args()
    main(args.duration, args.out)
