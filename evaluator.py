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
    """Runs generated code — pass if it executes and defines a function."""
    try:
        exec_globals = {}
        exec(output, exec_globals)
        has_function = any(callable(v) for v in exec_globals.values())
        if has_function:
            return True, "automated (exec + function check)"
        return False, "automated (exec ok but no function)"
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
        Scores the output.
        - B1 always uses code execution.
        - Others use DeepEval (if use_deepeval=True) else heuristic.
        """
        if self.task_id == "B1":
            self.success, self.score_method = check_code_execution(self.output)
            return

        if use_deepeval:
            # Import here so the project still runs even if deepeval
            # isn't installed (for the heuristic-only mode).
            from deepeval_scorer import score_with_deepeval
            result = score_with_deepeval(self.task_id, self.input_text, self.output)
            if result["score"] is not None:
                self.score        = result["score"]
                self.success      = result["passed"]
                self.reason       = result["reason"]
                self.score_method = f"DeepEval GEval ({result['score']})"
                return
            # fall through to heuristic if no config

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
            f"{r.latency_s}s",
            r.cloud_calls,
            f"${r.cost_usd:.6f}",
            f"{r.data_kb:.2f} KB",
            r.score_method
        ])

    headers = ["Task", "Category", "Agent", "Result", "Score",
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
    print("="*100 + "\n")

    # Print DeepEval judge reasons separately (they're long)
    deepeval_results = [r for r in results if r.reason]
    if deepeval_results:
        print("  DeepEval Judge Reasons:")
        print("-"*100)
        for r in deepeval_results:
            print(f"  [{r.task_id}] score={r.score} — {r.reason}")
        print("="*100 + "\n")
