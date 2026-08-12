# ============================================================
# run_experiments.py — Automated Experiment Sweep
# ============================================================
# Runs the full benchmark across every combination of:
#   system mode  x  local model
# Each combination runs main.py as a separate subprocess with
# environment variables set, so a crash in one run does not
# kill the whole sweep. All results append to results/results.csv.
#
# Run inside tmux — the full sweep takes hours:
#   tmux new -s sweep
#   python run_experiments.py
#   (Ctrl+B then D to detach)
# ============================================================

import os
import subprocess
import time
from datetime import datetime

# ── WHAT TO SWEEP ───────────────────────────────────────────

# How many times to repeat the entire sweep, so results can be
# reported as mean +/- standard deviation rather than single points.
REPEATS = 3

# Local models to test (the size ladder + quantization pair + specialist)
LOCAL_MODELS = [
    "qwen2.5:0.5b",
    "qwen2.5:1.5b",
    "qwen2.5:3b",
    "qwen2.5:7b",                  # this IS the q4_K_M quant
    "qwen2.5:7b-instruct-q8_0",    # q8 for the quantization comparison
    "llama3.2:3b",                 # cross-family check
]

VISION_MODELS = ["qwen2.5vl:3b", "llava:7b"]  # use your exact tags

# System modes. cloud_only does not depend on the local model,
# so it is run once separately rather than for every model.
LOCAL_DEPENDENT_MODES = ["local_only", "hybrid"]

def run_one(system_mode, local_model, vision_model=None, repeat=1):
    env = os.environ.copy()
    env["ECS_SYSTEM_MODE"] = system_mode
    env["ECS_LOCAL_MODEL"] = local_model
    if vision_model:
        env["ECS_VISION_MODEL"] = vision_model

    label = f"rep{repeat} | {system_mode} | {local_model}"
    print(f"\n{'='*70}")
    print(f"  RUN: {label}")
    print(f"  Started: {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*70}\n")

    start = time.time()
    try:
        # capture_output=False so you can watch progress live in tmux
        result = subprocess.run(
            ["python", "main.py"],
            env=env,
            timeout=7200   # 2 hour ceiling per run, so one hang cannot stall the sweep
        )
        status = "OK" if result.returncode == 0 else f"FAILED (exit {result.returncode})"
    except subprocess.TimeoutExpired:
        status = "TIMEOUT"
    except Exception as e:
        status = f"ERROR: {e}"

    mins = round((time.time() - start) / 60, 1)
    print(f"\n  --> {label}: {status}  ({mins} min)\n")
    return label, status, mins


def main():
    print("\n" + "="*70)
    print("  EDGE-CLOUD SWARM — EXPERIMENT SWEEP")
    print(f"  Repeats: {REPEATS}")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)

    summary = []

    for rep in range(1, REPEATS + 1):
        print(f"\n{'#'*70}")
        print(f"  REPEAT {rep} OF {REPEATS}")
        print(f"{'#'*70}\n")

        # Cloud-only baseline — local model is irrelevant here
        summary.append(run_one("cloud_only", "n/a", repeat=rep))

        # Every local model, in both local-only and hybrid modes
        for model in LOCAL_MODELS:
            for mode in LOCAL_DEPENDENT_MODES:
                summary.append(run_one(mode, model,
                                       vision_model=VISION_MODELS[0],
                                       repeat=rep))

        # Dedicated vision comparison — text model held constant
        for vm in VISION_MODELS:
            summary.append(run_one("local_only", "qwen2.5:3b",
                                   vision_model=vm, repeat=rep))

    # ── FINAL SUMMARY ───────────────────────────────────────
    print("\n" + "="*70)
    print("  SWEEP COMPLETE")
    print("="*70)
    total = 0
    for label, status, mins in summary:
        print(f"  {status:<22} {mins:>6} min   {label}")
        total += mins
    print(f"\n  Total runs: {len(summary)}   Total time: {round(total/60,1)} hours")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()