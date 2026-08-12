# ============================================================
# deepeval_scorer.py — DeepEval Integration (GEval)
# ============================================================
# Scores an agent's output using DeepEval's GEval metric.
#
# Criteria and expected outputs are NO LONGER hardcoded here —
# they come from the task definition in benchmark.py. This file
# just applies whichever scoring mode the task asks for.
#
# SCORING MODES:
#   "expected"      -> judge actual_output against expected_output
#   "criteria_only" -> judge actual_output against criteria alone
#                      (for ambiguous tasks with no single right answer)
#   "execution"     -> handled in evaluator.py, not here
# ============================================================

from deepeval.test_case import LLMTestCase, LLMTestCaseParams
from deepeval.metrics import GEval
from config import DEEPEVAL_MODEL, PASS_THRESHOLD


def score_with_deepeval(task_id, task_input, agent_output, criteria,
                        expected_output=None, scoring_mode="expected"):
    """
    Scores one task output with GEval.

    Args:
        task_id:        e.g. "A1" (used only for naming the metric)
        task_input:     what was given to the agent
        agent_output:   what the agent produced
        criteria:       natural-language description of what "good" looks like
        expected_output: reference answer (only used in "expected" mode)
        scoring_mode:   "expected" or "criteria_only"

    Returns:
        dict with score (0-1), passed (bool), reason (str)
    """

    # No criteria defined = nothing to judge against
    if not criteria:
        return {"score": None, "passed": None,
                "reason": "No GEval criteria defined for this task.",
                "judge_cost_usd": 0.0, "judge_tokens": 0}

    # Guard: GEval errors on empty output, so catch it early
    if not agent_output or not agent_output.strip():
        return {"score": 0.0, "passed": False,
                "reason": "Agent produced no output.",
                "judge_cost_usd": 0.0, "judge_tokens": 0}

    # Which fields the judge is allowed to look at.
    # In criteria_only mode we deliberately EXCLUDE expected_output,
    # because ambiguous tasks have no single correct answer.
    if scoring_mode == "criteria_only":
        eval_params = [
            LLMTestCaseParams.INPUT,
            LLMTestCaseParams.ACTUAL_OUTPUT,
        ]
        test_case = LLMTestCase(
            input=task_input,
            actual_output=agent_output
        )
    else:  # "expected" mode
        eval_params = [
            LLMTestCaseParams.INPUT,
            LLMTestCaseParams.ACTUAL_OUTPUT,
            LLMTestCaseParams.EXPECTED_OUTPUT,
        ]
        test_case = LLMTestCase(
            input=task_input,
            actual_output=agent_output,
            expected_output=expected_output
        )

    metric = GEval(
        name=f"Correctness-{task_id}",
        criteria=criteria,
        evaluation_params=eval_params,
        model=DEEPEVAL_MODEL,
        threshold=PASS_THRESHOLD
    )

    metric.measure(test_case)
    # Capture the judge's own cost and tokens so evaluation overhead can be
    # reported separately from the system's operational cost.
    judge_cost   = getattr(metric, "evaluation_cost", 0.0) or 0.0
    judge_in     = getattr(metric, "input_tokens", 0) or 0
    judge_out    = getattr(metric, "output_tokens", 0) or 0
    # Capture the judge's own token usage so evaluation cost can be
    # reported separately from system cost.
    judge_tokens = 0
    try:
        judge_tokens = getattr(metric, "evaluation_cost", 0) or 0
    except Exception:
        judge_tokens = 0

    return {
        "score": round(metric.score, 3),
        "passed": metric.score >= metric.threshold,
        "reason": metric.reason,
        "judge_cost_usd": round(judge_cost, 8),
        "judge_tokens": judge_in + judge_out
    }