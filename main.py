# ============================================================
# main.py — Entry Point (Full Pipeline + DeepEval)
# ============================================================
# Run with:
#   python main.py
#
# Flow:
#   1. Enter your OpenAI API key
#   2. Cloud CEO plans task delegation
#   3. Each agent runs (A,B,C,D local via Ollama; E cloud vision)
#   4. Outputs are scored:
#        - B1 by code execution
#        - A1,C1,D1,E1 by DeepEval GEval (LLM-as-judge)
#   5. Cloud CEO synthesizes a final summary
#   6. Full evaluation table prints (with DeepEval scores)
#
# Toggle USE_DEEPEVAL below to switch between DeepEval scoring
# and the simple keyword heuristic.
# ============================================================

import os
import openai

from orchestrator import plan_tasks, synthesize_results
from agents.file_agent       import run as run_file_agent
from agents.code_agent       import run as run_code_agent
from agents.planning_agent   import run as run_planning_agent
from agents.document_agent   import run as run_document_agent
from agents.multimodal_agent import run as run_multimodal_agent
from evaluator import TaskResult, print_results_table

# ── TOGGLE: True = DeepEval scoring, False = keyword heuristic ──
USE_DEEPEVAL = True


TASKS = [
    {"id": "A1", "category": "A-File/Log",   "description": "Read the server log and extract all ERROR-level events with timestamps, then summarise the root cause in one sentence.", "agent": "file_agent"},
    {"id": "B1", "category": "B-Code",       "description": "Write a Python function is_prime(n) that returns True if n is prime, else False.", "agent": "code_agent"},
    {"id": "C1", "category": "C-Planning",   "description": "Decompose: build a data pipeline that reads CSV files, cleans the data, and outputs a summary report.", "agent": "planning_agent"},
    {"id": "D1", "category": "D-Document",   "description": "Summarise the provided edge computing document in 2-3 sentences.", "agent": "document_agent"},
    {"id": "E1", "category": "E-Multimodal", "description": "Analyse the provided screenshot and describe any errors/issues, then suggest a fix.", "agent": "multimodal_agent"},
]


def main():
    print("\n" + "="*60)
    print("  The Edge-Cloud Swarm — 5-Task Prototype")
    print(f"  Scoring mode: {'DeepEval (GEval)' if USE_DEEPEVAL else 'Keyword heuristic'}")
    print("="*60)

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        api_key = input("\nEnter your OpenAI API key: ").strip()
        os.environ["OPENAI_API_KEY"] = api_key   # DeepEval reads this too

    client = openai.OpenAI(api_key=api_key)

    # ── STEP 1: PLAN ─────────────────────────────────────────
    print("\n[1/4] Cloud CEO planning task delegation...")
    plan_result = plan_tasks(TASKS, client)
    for item in plan_result["plan"]:
        print(f"      -> Task {item.get('task_id','?')} -> {item.get('agent','?')}: {item.get('reason','')}")

    # ── STEP 2: LOAD INPUTS ─────────────────────────────────
    with open("tasks/sample_log.txt") as f:
        log_content = f.read()
    with open("tasks/sample_document.txt") as f:
        doc_content = f.read()

    screenshot_path = "tasks/error_screenshot.png"
    has_screenshot  = os.path.exists(screenshot_path)

    # ── STEP 3: RUN AGENTS ──────────────────────────────────
    print("\n[2/4] Running agents...")
    results = []

    # A1 — File Agent (LOCAL)
    print("  A1 - File Agent (LOCAL)...")
    r = TaskResult("A1", "A-File/Log", "file_agent [LOCAL]")
    r.input_text = "Extract ERROR-level events from the server log and summarise the root cause."
    r.start(); r.output = run_file_agent(log_content); r.stop()
    r.finalise(use_deepeval=USE_DEEPEVAL); results.append(r)

    # B1 — Code Agent (LOCAL)
    print("  B1 - Code Agent (LOCAL)...")
    r = TaskResult("B1", "B-Code", "code_agent [LOCAL]")
    r.input_text = "Write a Python function is_prime(n)."
    r.start(); r.output = run_code_agent("Write a Python function called is_prime(n) that returns True if n is prime."); r.stop()
    r.finalise(use_deepeval=USE_DEEPEVAL); results.append(r)

    # C1 — Planning Agent (LOCAL)
    print("  C1 - Planning Agent (LOCAL)...")
    r = TaskResult("C1", "C-Planning", "planning_agent [LOCAL]")
    r.input_text = "Decompose: build a data pipeline that reads CSVs, cleans data, outputs a summary."
    r.start(); r.output = run_planning_agent("Build a data pipeline that reads CSV files, cleans the data, and outputs a summary report."); r.stop()
    r.finalise(use_deepeval=USE_DEEPEVAL); results.append(r)

    # D1 — Document Agent (LOCAL)
    print("  D1 - Document Agent (LOCAL)...")
    r = TaskResult("D1", "D-Document", "document_agent [LOCAL]")
    r.input_text = "Summarise the edge computing document in 2-3 sentences."
    r.start(); r.output = run_document_agent(doc_content); r.stop()
    r.finalise(use_deepeval=USE_DEEPEVAL); results.append(r)

    # E1 — Multimodal Agent (CLOUD)
    print("  E1 - Multimodal Agent (CLOUD)...")
    r = TaskResult("E1", "E-Multimodal", "multimodal_agent [CLOUD]")
    r.input_text = "Analyse the screenshot and describe the error, then suggest a fix."
    r.start()
    if has_screenshot:
        e1 = run_multimodal_agent(screenshot_path, client)
        r.output = e1["response"]
        r.record_cloud_call(e1["tokens_used"], "image_task", model="gpt-4o")
        r.finalise(use_deepeval=USE_DEEPEVAL)
    else:
        r.output = "[SKIPPED] No screenshot at tasks/error_screenshot.png. Add any screenshot to test this task."
        r.success = None
    r.stop()
    results.append(r)

    # ── STEP 4: SYNTHESIZE ──────────────────────────────────
    print("\n[3/4] Cloud CEO synthesizing final results...")
    synthesis_input = [
        {"task_id": r.task_id, "agent": r.agent, "output": r.output}
        for r in results if r.output and "[SKIPPED]" not in r.output
    ]
    synthesis = synthesize_results(synthesis_input, client)

    # ── OUTPUTS ─────────────────────────────────────────────
    print("\n[4/4] Agent Outputs:")
    print("-"*60)
    for r in results:
        print(f"\n  [{r.task_id}] {r.category}  ({r.agent})")
        print(f"  {r.output[:400]}{'...' if len(r.output) > 400 else ''}")

    print("\n  FINAL SYNTHESIS (Cloud CEO):")
    print("-"*60)
    print(synthesis["summary"])

    print_results_table(results)


if __name__ == "__main__":
    main()
