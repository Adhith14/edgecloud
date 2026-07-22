# ============================================================
# deepeval_scorer.py — DeepEval Integration (GEval)
# ============================================================
# This module wires DeepEval's GEval metric into the pipeline,
# replacing the simple keyword-heuristic scoring with real
# LLM-as-judge scoring.
#
# HOW GEval WORKS:
#   1. You define a natural-language CRITERIA (what "good" means)
#   2. You give it the actual_output (what the agent produced)
#      and an expected_output (a reference "ideal" answer)
#   3. GEval uses an LLM judge (gpt-4o-mini here) to score how
#      well actual_output meets the criteria, from 0.0 to 1.0
#   4. score >= threshold (0.5) = PASS. It also returns a REASON.
#
# Needs OPENAI_API_KEY as an environment variable, because GEval
# itself calls an LLM to do the judging.
# ============================================================

from deepeval.test_case import LLMTestCase, LLMTestCaseParams
from deepeval.metrics import GEval
from config import DEEPEVAL_MODEL, PASS_THRESHOLD

# One judging config per task. "criteria" tells the judge what to
# look for; "expected_output" is the reference ideal answer.
TASK_EVAL_CONFIG = {
    "A1": {
        "criteria": (
            "Determine whether the actual output correctly identifies the "
            "ERROR-level log lines from the server log and gives a sensible "
            "one-sentence root cause summary. It should mention the cache "
            "connection failure and/or the payment processing timeout, since "
            "those are the real errors in the log."
        ),
        "expected_output": (
            "The errors found are: cache service connection failure after 3 "
            "retries, a NullPointerException in OrderService.processOrder(), and "
            "a payment processing timeout for order_id=9921. The root cause "
            "appears to be cascading failures starting with the cache outage."
        )
    },
    "C1": {
        "criteria": (
            "Determine whether the actual output decomposes the goal into "
            "logical, ordered subtasks that would achieve building a data "
            "pipeline that reads CSVs, cleans data, and outputs a summary. "
            "Steps should include reading/loading data, cleaning/validating it, "
            "and producing a summary or report."
        ),
        "expected_output": (
            "1. Read CSV files into a data structure. 2. Validate and clean the "
            "data. 3. Perform aggregation or analysis. 4. Generate a summary "
            "report. 5. Output or save the report."
        )
    },
    "D1": {
        "criteria": (
            "Determine whether the actual output is a faithful, concise 2-3 "
            "sentence summary of the document about edge computing. It should "
            "mention that edge computing processes data locally, and reference "
            "at least one benefit (privacy or reduced latency) or one challenge "
            "(limited local compute resources)."
        ),
        "expected_output": (
            "Edge computing processes data locally on devices rather than "
            "sending it to the cloud, reducing latency and protecting privacy. "
            "However, local devices have limited compute resources, restricting "
            "the size of models that can run there."
        )
    },
    "E1": {
        "criteria": (
            "Determine whether the actual output correctly identifies that the "
            "image shows an error or issue, and gives a plausible, specific fix. "
            "Vague answers that do not engage with details in the image should "
            "score lower."
        ),
        "expected_output": (
            "The output should name the specific error or problem visible in the "
            "screenshot and suggest a concrete, relevant fix."
        )
    },
}


def score_with_deepeval(task_id: str, agent_input: str, agent_output: str) -> dict:
    """
    Scores one task's output using DeepEval's GEval metric.

    Returns dict with: score (0-1 float), passed (bool), reason (str).
    Code tasks (B1) are NOT scored here — they use direct execution
    in evaluator.py, which is more reliable than an LLM judge.
    """
    config = TASK_EVAL_CONFIG.get(task_id)
    if not config:
        return {"score": None, "passed": None,
                "reason": "No GEval config for this task (e.g. code task uses execution)."}

    correctness_metric = GEval(
        name=f"Correctness-{task_id}",
        criteria=config["criteria"],
        evaluation_params=[
            LLMTestCaseParams.INPUT,
            LLMTestCaseParams.ACTUAL_OUTPUT,
            LLMTestCaseParams.EXPECTED_OUTPUT,
        ],
        model=DEEPEVAL_MODEL,
        threshold=PASS_THRESHOLD
    )

    test_case = LLMTestCase(
        input=agent_input,
        actual_output=agent_output,
        expected_output=config["expected_output"]
    )

    correctness_metric.measure(test_case)

    return {
        "score": round(correctness_metric.score, 3),
        "passed": correctness_metric.score >= correctness_metric.threshold,
        "reason": correctness_metric.reason
    }
