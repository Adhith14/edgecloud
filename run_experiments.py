# ============================================================
# run_experiments.py — Automated Experiment Sweep
# ============================================================
# Runs the full benchmark across every experimental condition.
# Each run is a separate subprocess with environment variables
# set, so a crash in one condition cannot kill the whole sweep.
# All results append to results/results.csv and results/runs.csv.
#
# Run inside tmux — the full sweep takes many hours:
#   tmux new -s sweep
#   python run_experiments.py
#   (Ctrl+B then D to detach)
# ============================================================

import os
import subprocess
import time
from datetime import datetime

# ── SWEEP CONFIGURATION ─────────────────────────────────────

REPEATS = 3

# Text model sizes for the v1 scale study. Tool use is unreliable
# below 3B, so v2 conditions use only the larger two.
V1_MODELS = ["qwen2.5:0.5b", "qwen2.5:1.5b", "qwen2.5:3b", "qwen2.5:7b"]
V2_MODELS = ["qwen2.5:3b", "qwen2.5:7b"]

# Quantisation comparison, v1 only (isolates precision from architecture)
QUANT_MODELS = ["qwen2.5:7b", "qwen2.5:7b-instruct-q8_0"]

# Vision comparison, held at a fixed text model
VISION_MODELS = ["qwen2.5vl:3b", "llava:7b"]
PRIMARY_VISION = "qwen2.5vl:3b"

# Per-run wall-clock ceiling. v2 runs with retries can exceed 20 min,
# so this is generous; it only guards against a genuine hang.
RUN_TIMEOUT_S = 7200 


def run_one(system_mode, local_model, assignment="specialist",
            vision_model=PRIMARY_VISION, repeat=1, note=""):
    """Runs main.py once with the given configuration."""
    env = os.environ.copy()
    env["ECS_SYSTEM_MODE"] = system_mode
    env["ECS_LOCAL_MODEL"] = local_model
    env["ECS_MODEL_ASSIGNMENT"] = assignment
    env["ECS_VISION_MODEL"] = vision_model
    # v2 specialist models follow the sweep's text model where relevant
    env["ECS_SHARED_MODEL"] = local_model
    env["ECS_FILE_MODEL"] = local_model
    env["ECS_PLAN_MODEL"] = local_model

    label = f"rep{repeat} | {system_mode} | {local_model} | {assignment} | {vision_model}"
    if note:
        label += f" | {note}"

    print(f"\n{'='*72}")
    print(f"  {label}")
    print(f"  Started: {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*72}\n")

    start = time.time()
    try:
        result = subprocess.run(["python", "main.py"], env=env, timeout=RUN_TIMEOUT_S)
        status = "OK" if result.returncode == 0 else f"FAILED (exit {result.returncode})"
    except subprocess.TimeoutExpired:
        status = "TIMEOUT"
    except Exception as e:
        status = f"ERROR: {str(e)[:40]}"

    mins = round((time.time() - start) / 60, 1)
    print(f"\n  --> {status}  ({mins} min)  {label}\n")
    return label, status, mins


# def main():
#     print("\n" + "="*72)
#     print("  EDGE-CLOUD SWARM — FULL EXPERIMENT SWEEP")
#     print(f"  Repeats: {REPEATS}")
#     print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
#     print("="*72)

#     summary = []

#     for rep in range(1, REPEATS + 1):
#         print(f"\n{'#'*72}\n  REPEAT {rep} OF {REPEATS}\n{'#'*72}")

#         # ── 1. Cloud baseline (local model irrelevant) ──────
#         summary.append(run_one("cloud_only", "n/a", repeat=rep))

#         # ── 2. v1 scale study: local-only and hybrid ────────
#         for model in V1_MODELS:
#             summary.append(run_one("local_only", model, repeat=rep))
#             summary.append(run_one("hybrid", model, repeat=rep))

#         # ── 3. Quantisation comparison (q8 only; q4 covered above) ──
#         summary.append(run_one("local_only", "qwen2.5:7b-instruct-q8_0",
#                                repeat=rep, note="quant"))

#         # ── 4. v2: tools, specialists, iteration ────────────
#         for model in V2_MODELS:
#             for mode in ["v2_local", "v2_hybrid"]:
#                 for assign in ["specialist", "shared_generalist"]:
#                     summary.append(run_one(mode, model, assignment=assign, repeat=rep))

#         # ── 5. Vision model comparison (fixed text model) ───
#         for vm in VISION_MODELS:
#             if vm == PRIMARY_VISION:
#                 continue     # already covered by the runs above
#             summary.append(run_one("local_only", "qwen2.5:3b",
#                                    vision_model=vm, repeat=rep, note="vision"))

#     # ── FINAL SUMMARY ───────────────────────────────────────
#     print("\n" + "="*72)
#     print("  SWEEP COMPLETE")
#     print("="*72)
#     total = 0
#     for label, status, mins in summary:
#         print(f"  {status:<20} {mins:>7} min   {label}")
#         total += mins
#     print(f"\n  Runs: {len(summary)}   Total: {round(total/60,1)} hours")
#     print("="*72 + "\n")


def main():
    print("\n" + "="*72)
    print("  V2 SWEEP (completing missing conditions)")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*72)

    summary = []
    for rep in range(1, REPEATS + 1):
        print(f"\n{'#'*72}\n  REPEAT {rep} OF {REPEATS}\n{'#'*72}")
        for model in V2_MODELS:
            for mode in ["v2_local", "v2_hybrid"]:
                for assign in ["specialist", "shared_generalist"]:
                    summary.append(run_one(mode, model, assignment=assign, repeat=rep))

    print("\n" + "="*72)
    print("  SWEEP COMPLETE")
    print("="*72)
    total = 0
    for label, status, mins in summary:
        print(f"  {status:<20} {mins:>7} min   {label}")
        total += mins
    print(f"\n  Runs: {len(summary)}   Total: {round(total/60,1)} hours")
    print("="*72 + "\n")


if __name__ == "__main__":
    main()