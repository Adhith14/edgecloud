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
import config

from orchestrator import plan_tasks, synthesize_results
from agents.file_agent       import run as run_file_agent
from agents.code_agent       import run as run_code_agent
from agents.planning_agent   import run as run_planning_agent
from agents.document_agent   import run as run_document_agent
from agents.multimodal_agent import run as run_multimodal_agent
from evaluator import TaskResult, print_results_table, save_results_csv
from escalation import escalate_to_cloud
from evaluator import calculate_cost

TASKS = [
    {"id": "A1", "category": "A-File/Log",   "description": "Read the server log and extract all ERROR-level events with timestamps, then summarise the root cause in one sentence.", "agent": "file_agent"},
    {"id": "B1", "category": "B-Code",       "description": "Write a Python function is_prime(n) that returns True if n is prime, else False.", "agent": "code_agent"},
    {"id": "C1", "category": "C-Planning",   "description": "Decompose: build a data pipeline that reads CSV files, cleans the data, and outputs a summary report.", "agent": "planning_agent"},
    {"id": "D1", "category": "D-Document",   "description": "Summarise the provided edge computing document in 2-3 sentences.", "agent": "document_agent"},
    {"id": "E1", "category": "E-Multimodal", "description": "Analyse the provided screenshot and describe any errors/issues, then suggest a fix.", "agent": "multimodal_agent"},
]


def handle_escalation(r, task_description, task_input, client):
    """
    Checks whether a local task result should be escalated to the cloud.
    Called AFTER the local agent has run and been scored.

    Logic (Option A - score-based):
      - If escalation is enabled AND the task has a DeepEval score AND
        that score is below the escalation threshold → escalate to cloud.
      - The cloud's answer replaces the local output.
      - We keep a record of the original local output and score.

    Args:
        r: the TaskResult object (already scored)
        task_description: what the task asked for
        task_input: the data given to the task
        client: OpenAI client
    """
    # Only escalate if enabled in config
    if not config.ENABLE_ESCALATION:
        return

    # We can only score-escalate tasks that have a numeric DeepEval score.
    # (B1 code tasks use execution, not a score — skip those here.)
    if r.score is None:
        return

    # The decision: is the local score below the threshold?
    if r.score < config.ESCALATION_THRESHOLD:
        print(f"    [ESCALATION] {r.task_id} scored {r.score} < {config.ESCALATION_THRESHOLD} — escalating to cloud...")

        # Remember what the local model produced before we replace it
        r.local_output = r.output
        r.local_score  = r.score

        # Send the task to the cloud for a better answer
        cloud_result = escalate_to_cloud(task_description, task_input, client)

        # Replace the output with the cloud's answer
        r.output = cloud_result["output"]

        # Record that this task was escalated, and log the cloud call
        r.escalated = True
        r.record_cloud_call(cloud_result["tokens_used"], task_input, model=config.CLOUD_ESCALATION_MODEL)

        # Re-score the new cloud output so the final score reflects the escalated answer
        r.finalise(use_deepeval=config.USE_DEEPEVAL)

        print(f"    [ESCALATION] {r.task_id} re-scored after cloud: {r.score}")
    else:
        print(f"    [LOCAL OK] {r.task_id} scored {r.score} — kept local, no escalation.")


def main():
    print("\n" + "="*60)
    print("  The Edge-Cloud Swarm — 5-Task Prototype")
    print(f"  Scoring mode: {'DeepEval (GEval)' if config.USE_DEEPEVAL else 'Keyword heuristic'}")
    print("="*60)

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found. Add it to your .env file.")

    client = openai.OpenAI(api_key=api_key)

    # ── STEP 1: PLAN ─────────────────────────────────────────
    print("\n[1/4] Cloud CEO planning task delegation...")
    plan_result = plan_tasks(TASKS, client)
    orchestration_tokens = plan_result["tokens_used"]
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
    r.finalise(use_deepeval=config.USE_DEEPEVAL)
    handle_escalation(r, "Extract ERROR-level events from the server log and summarise the root cause.", log_content, client)
    results.append(r)

    # B1 — Code Agent (LOCAL)
    print("  B1 - Code Agent (LOCAL)...")
    r = TaskResult("B1", "B-Code", "code_agent [LOCAL]")
    r.input_text = "Write a Python function is_prime(n)."
    r.start(); r.output = run_code_agent("Write a Python function called is_prime(n) that returns True if n is prime."); r.stop()
    r.finalise(use_deepeval=config.USE_DEEPEVAL); results.append(r)

    # C1 — Planning Agent (LOCAL)
    print("  C1 - Planning Agent (LOCAL)...")
    r = TaskResult("C1", "C-Planning", "planning_agent [LOCAL]")
    r.input_text = "Decompose: build a data pipeline that reads CSVs, cleans data, outputs a summary."
    r.start(); r.output = run_planning_agent("Build a data pipeline that reads CSV files, cleans the data, and outputs a summary report."); r.stop()
    r.finalise(use_deepeval=config.USE_DEEPEVAL)
    handle_escalation(r, "Decompose into ordered subtasks: build a data pipeline that reads CSV files, cleans the data, and outputs a summary report.", "Build a data pipeline that reads CSV files, cleans the data, and outputs a summary report.", client)
    results.append(r)

    # D1 — Document Agent (LOCAL)
    print("  D1 - Document Agent (LOCAL)...")
    r = TaskResult("D1", "D-Document", "document_agent [LOCAL]")
    r.input_text = "Summarise the edge computing document in 2-3 sentences."
    r.start(); r.output = run_document_agent(doc_content); r.stop()
    r.finalise(use_deepeval=config.USE_DEEPEVAL)
    handle_escalation(r, "Summarise the provided document in 2-3 sentences.", doc_content, client)
    results.append(r)

    # E1 — Multimodal Agent (CLOUD)
    print("  E1 - Multimodal Agent (CLOUD)...")
    r = TaskResult("E1", "E-Multimodal", "multimodal_agent [CLOUD]")
    r.input_text = "Analyse the screenshot and describe the error, then suggest a fix."
    r.start()
    if has_screenshot:
        e1 = run_multimodal_agent(screenshot_path, client)
        r.output = e1["response"]
        r.record_cloud_call(e1["tokens_used"], "image_task", model="gpt-4o")
        r.finalise(use_deepeval=config.USE_DEEPEVAL)
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
    orchestration_tokens += synthesis["tokens_used"]

    # ── OUTPUTS ─────────────────────────────────────────────
    print("\n[4/4] Agent Outputs:")
    print("-"*60)
    for r in results:
        print(f"\n  [{r.task_id}] {r.category}  ({r.agent})")
        print(f"  {r.output[:400]}{'...' if len(r.output) > 400 else ''}")

    print("\n  FINAL SYNTHESIS (Cloud CEO):")
    print("-"*60)
    print(synthesis["summary"])

    # Calculate the orchestrator's own cost (planning + synthesis)
    orchestration_cost = calculate_cost(orchestration_tokens, config.CLOUD_ORCHESTRATOR_MODEL)
    print(f"\n  Orchestration overhead: {orchestration_tokens} tokens  =  ${orchestration_cost:.6f}")
    print(f"  (This is the cost of the cloud CEO planning and synthesis, separate from per-task costs)")

    print_results_table(results)
    save_results_csv(results, model_name=config.LOCAL_MODEL)


if __name__ == "__main__":
    main()
