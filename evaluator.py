# ============================================================
# evaluator.py — Evaluation and Logging
# ============================================================
# Records the 5 project metrics per task:
#   1. Task Success Rate (%)  — did it produce a usable output?
#   2. End-to-End Latency (s) — how long did the task take?
#   3. Estimated API Cost ($) — cost based on tokens used
#   4. Cloud API Calls (#)    — how many cloud calls were made?
#   5. Data Sent to Cloud(KB) — how much data went to the cloud?
#
# SUCCESS SCORING:
#   - Code task (B1): direct execution (run the code)
#   - Other tasks: DeepEval GEval (LLM-as-judge) IF enabled,
#     otherwise a simple keyword heuristic fallback.
# ============================================================

import time
from tabulate import tabulate
import csv
import os
from datetime import datetime
import config

# ── OpenAI pricing (approx, gpt-4o-mini & gpt-4o, 2026) ──────
GPT4O_MINI_INPUT_COST_PER_1K  = 0.000150
GPT4O_MINI_OUTPUT_COST_PER_1K = 0.000600
GPT4O_INPUT_COST_PER_1K       = 0.002500
GPT4O_OUTPUT_COST_PER_1K      = 0.010000


def calculate_cost(tokens: int, model: str = "gpt-4o-mini") -> float:
    """Estimates USD cost of a cloud call. Local Ollama calls are $0."""
    if model == "gpt-4o-mini":
        cost = (tokens * 0.6 / 1000 * GPT4O_MINI_INPUT_COST_PER_1K +
                tokens * 0.4 / 1000 * GPT4O_MINI_OUTPUT_COST_PER_1K)
    elif model == "gpt-4o":
        cost = (tokens * 0.6 / 1000 * GPT4O_INPUT_COST_PER_1K +
                tokens * 0.4 / 1000 * GPT4O_OUTPUT_COST_PER_1K)
    else:
        cost = 0.0
    return round(cost, 6)


def check_success_heuristic(task_id: str, output: str):
    """Simple keyword-based fallback scoring (used if DeepEval is off)."""
    if not output or len(output.strip()) < 20:
        return False, "heuristic (output too short)"

    expected_keywords = {
        "A1": ["error", "failed", "exception", "cache", "payment"],
        "C1": ["step", "1.", "pipeline", "data", "read", "clean", "output"],
        "D1": ["edge", "comput", "privac", "model", "local", "cloud"],
        "E1": ["error", "issue", "problem", "fix", "suggest", "screen"],
    }
    keywords = expected_keywords.get(task_id, [])
    if not keywords:
        return len(output.strip()) > 30, "heuristic (non-empty)"
    found = any(kw.lower() in output.lower() for kw in keywords)
    return found, "heuristic (keyword match)"


def check_code_execution(output: str):
    """Runs generated code — pass if it executes and defines a function.

    v2 agents sometimes wrap code in markdown fences or add commentary,
    so we extract the code block first where one is present.
    """
    code = output or ""

    # Prefer the contents of a fenced block if there is one
    if "```" in code:
        parts = code.split("```")
        if len(parts) >= 2:
            block = parts[1]
            lines = block.split("\n")
            if lines and lines[0].strip().lower() in ("python", "py", ""):
                block = "\n".join(lines[1:])
            code = block

    # Normalise smart quotes, which break exec()
    code = (code.replace("\u2019", "'").replace("\u2018", "'")
                .replace("\u201c", '"').replace("\u201d", '"'))

    try:
        exec_globals = {}
        exec(code, exec_globals)
        # Code ran without raising. That is the real success criterion.
        # A defined function is a stronger signal, so we note it, but its
        # absence should not fail otherwise-working code.
        has_function = any(callable(v) for v in exec_globals.values()
                           if not str(v).startswith("<built-in"))
        if has_function:
            return True, "automated (exec + function defined)"
        return True, "automated (exec ok, no function defined)"
    except Exception as e:
        return False, f"automated (exec failed: {str(e)[:40]})"


class TaskResult:
    """Stores all evaluation data for a single task run."""
    def __init__(self, task_id, category, agent):
        self.task_id      = task_id
        self.category     = category
        self.agent        = agent
        self.input_text   = ""     # what was given to the agent
        self.output       = ""
        self.latency_s    = 0.0
        self.cloud_calls  = 0
        self.tokens_used  = 0
        self.cost_usd     = 0.0
        self.data_kb      = 0.0
        self.success      = False
        self.score        = None   # DeepEval numeric score (0-1), if used
        self.score_method = ""
        self.reason       = ""     # DeepEval judge reason, if used
        self.start_time   = None
        self.escalated       = False   # True if this task was escalated to cloud
        self.local_score     = None    # the local model's score before escalation
        self.local_output    = ""      # what the local agent produced (kept for the record)
    
        self.scoring_mode    = "expected"
        self.criteria        = None
        self.expected_output = None
        # Evaluation overhead — the judge's own cost, kept separate from
        # system cost because the judge only exists in the lab, not in
        # a real deployment.
        self.judge_cost_usd  = 0.0
        self.judge_tokens    = 0
        # V2 metrics — populated only when running through the graph
        self.iterations_used = 0      # how many specialist attempts (1 = no retry)
        self.tools_called    = []     # tool names used, in order
        self.models_used     = []     # which models participated
        self.critic_passed   = None   # did the LOCAL critic accept the output

    def start(self):
        self.start_time = time.time()

    def stop(self):
        self.latency_s = round(time.time() - self.start_time, 2)

    def record_cloud_call(self, tokens, prompt_text, model="gpt-4o-mini"):
        self.cloud_calls += 1
        self.tokens_used += tokens
        self.cost_usd    += calculate_cost(tokens, model)
        self.data_kb     += round(len(prompt_text.encode("utf-8")) / 1024, 3)

    def finalise(self, use_deepeval=False):
        """
        Scores the output according to this task's scoring_mode:
          "execution"     -> run the code, pass if it works
          "expected"      -> GEval against a reference answer
          "criteria_only" -> GEval against criteria alone (ambiguous tasks)
        """
        # Code tasks: run the code, no LLM judge needed
        if self.scoring_mode == "execution":
            self.success, self.score_method = check_code_execution(self.output)
            return

        # Everything else uses DeepEval, if it's switched on
        if use_deepeval:
            from deepeval_scorer import score_with_deepeval
            result = score_with_deepeval(
                task_id=self.task_id,
                task_input=self.input_text,
                agent_output=self.output,
                criteria=self.criteria,
                expected_output=self.expected_output,
                scoring_mode=self.scoring_mode
            )
            # Accumulate — a task scored twice (before and after escalation)

            # incurs judge cost twice, so we add rather than overwrite.

            self.judge_cost_usd += result.get("judge_cost_usd", 0.0)
            self.judge_tokens   += result.get("judge_tokens", 0)
            
            if result["score"] is not None:
                self.score        = result["score"]
                self.success      = result["passed"]
                self.reason       = result["reason"]
                self.score_method = f"DeepEval GEval ({result['score']})"
                return

        # Fallback if DeepEval is off or no criteria were defined
        self.success, self.score_method = check_success_heuristic(self.task_id, self.output)

def print_results_table(results):
    """Prints the evaluation table — this is what you show the supervisor."""
    rows = []
    for r in results:
        if r.success is None:
            success_str = "— SKIP"
        else:
            success_str = "PASS" if r.success else "FAIL"
        rows.append([
            r.task_id, r.category, r.agent,
            success_str,
            f"{r.score}" if r.score is not None else "-",
            "YES" if r.escalated else "no",
            f"{r.latency_s}s",
            r.cloud_calls,
            f"${r.cost_usd:.6f}",
            f"{r.data_kb:.2f} KB",
            r.score_method
        ])

    headers = ["Task", "Category", "Agent", "Result", "Score", "Escalated",
               "Latency", "Cloud", "Est.Cost", "Data->Cloud", "Method"]

    print("\n" + "="*100)
    print("  EVALUATION RESULTS — Edge-Cloud Swarm Prototype")
    print("="*100)
    print(tabulate(rows, headers=headers, tablefmt="rounded_outline"))

    scored = [r for r in results if r.success is not None]
    total  = len(scored)
    passed = sum(1 for r in scored if r.success)
    avg_lat = round(sum(r.latency_s for r in results) / len(results), 2)
    total_cost = sum(r.cost_usd for r in results)
    total_calls = sum(r.cloud_calls for r in results)

    if total > 0:
        print(f"\n  Overall Success Rate : {passed}/{total} tasks ({round(passed/total*100)}%)")
    print(f"  Average Latency      : {avg_lat}s per task")
    print(f"  Total Cloud API Calls: {total_calls}")
    print(f"  Total Estimated Cost : ${total_cost:.6f}")
    total_eval_cost = sum(r.judge_cost_usd for r in results)
    print(f"  Evaluation Overhead  : ${total_eval_cost:.6f}  (judge cost — lab only, not system cost)")
    print("="*100 + "\n")

    # Print DeepEval judge reasons separately (they're long)
    deepeval_results = [r for r in results if r.reason]
    if deepeval_results:
        print("  DeepEval Judge Reasons:")
        print("-"*100)
        for r in deepeval_results:
            print(f"  [{r.task_id}] score={r.score} — {r.reason}")
        print("="*100 + "\n")
        
        
def save_results_csv(results, model_name, system_name="edge-cloud-swarm", filepath="results/results.csv"):
    """
    Appends this run's results to a CSV file so they persist across runs.
    Each row = one task. A timestamp and model name tag every row so you
    can compare different runs and different models later.

    Args:
        results: list of completed TaskResult objects
        model_name: which local model was used (from config.LOCAL_MODEL)
        system_name: which system produced these (for later baseline comparison)
        filepath: where to save the CSV
    """
    # Make sure the results/ folder exists
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    # Check if the file already exists — if not, we'll write a header row first
    file_exists = os.path.isfile(filepath)

    # One timestamp for the whole run, so all rows from this run share it
    run_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open(filepath, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        # Write the header row only once (when the file is first created)
        if not file_exists:
            writer.writerow([
                "run_time", "system", "model", "vision_model", "task_id", "category", "agent",
                "success", "score", "escalated", "local_score", "latency_s", "cloud_calls",
                "cost_usd", "eval_cost_usd", "eval_tokens",
                "data_kb", "iterations_used", "tools_called",
                "models_used", "critic_passed",
                "score_method", "judge_reason"
            ])

        # Write one row per task
        for r in results:
            writer.writerow([
                run_time,
                system_name,
                model_name,
                config.LOCAL_VISION_MODEL,
                r.task_id,
                r.category,
                r.agent,
                r.success,          # True / False / None(skipped)
                r.score if r.score is not None else "",
                r.escalated,
                r.local_score if r.local_score is not None else "",
                r.latency_s,
                r.cloud_calls,
                round(r.cost_usd, 6),
                round(r.judge_cost_usd, 8),
                r.judge_tokens,
                round(r.data_kb, 3),
                r.iterations_used,
                "|".join(r.tools_called),          # pipe-separated, CSV-safe
                "|".join(r.models_used),
                r.critic_passed if r.critic_passed is not None else "",
                r.score_method,
                (r.reason or "").replace("\n", " ")[:500]
            ])

    print(f"\n  Results saved to {filepath}")
    
    
def save_run_summary(results, model_name, system_name, orchestration_tokens,
                     orchestration_cost, filepath="results/runs.csv"):

    """
    Saves ONE row per benchmark run, capturing run-level metrics that
    don't belong on individual tasks — chiefly the orchestrator's own
    planning and synthesis cost, plus aggregate totals.

    """
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    file_exists = os.path.isfile(filepath)
    run_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    scored = [r for r in results if r.success is not None]
    passed = sum(1 for r in scored if r.success)
    escalated = sum(1 for r in results if r.escalated)

    with open(filepath, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow([
                "run_time", "system", "model","model_assignment", "tasks_total", "tasks_scored",
                "tasks_passed", "success_rate_pct", "tasks_escalated",
                "orchestration_tokens", "orchestration_cost_usd",
                "task_cost_usd", "total_system_cost_usd",
                "eval_cost_usd", "total_latency_s", "total_data_kb",
                "total_iterations", "tasks_retried", "total_tool_calls","vision_model",
            ])


        task_cost = sum(r.cost_usd for r in results)
        writer.writerow([
            run_time, system_name, model_name, config.MODEL_ASSIGNMENT,
            len(results), len(scored), passed,
            round(passed / len(scored) * 100, 1) if scored else 0,
            escalated,
            orchestration_tokens,
            round(orchestration_cost, 8),
            round(task_cost, 8),
            round(task_cost + orchestration_cost, 8),   # true system cost
            round(sum(r.judge_cost_usd for r in results), 8),
            round(sum(r.latency_s for r in results), 2),
            round(sum(r.data_kb for r in results), 3),
            sum(r.iterations_used for r in results),
            sum(1 for r in results if r.iterations_used > 1),   # tasks needing a retry
            sum(len(r.tools_called) for r in results),
            config.LOCAL_VISION_MODEL,
        ])
    print(f"  Run summary saved to {filepath}")