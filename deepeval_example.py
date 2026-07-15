# ============================================================
# deepeval_example.py — STANDALONE DeepEval Demo
# ============================================================
# This is a minimal, self-contained example to show your
# supervisor exactly how DeepEval works — no agents, no Ollama,
# no pipeline. Just one input, one output, one score.
#
# Run it with:
#   python deepeval_example.py
#
# You must have OPENAI_API_KEY set, because DeepEval's GEval
# metric uses an LLM (gpt-4o-mini) as the "judge".
# ============================================================

import os
from deepeval.test_case import LLMTestCase, LLMTestCaseParams
from deepeval.metrics import GEval


def main():
    print("\n" + "="*70)
    print("  DeepEval Standalone Example — GEval (LLM-as-judge)")
    print("="*70)

    # ── 1. Make sure the API key is set ──────────────────────
    if not os.environ.get("OPENAI_API_KEY"):
        key = input("\nEnter your OpenAI API key: ").strip()
        os.environ["OPENAI_API_KEY"] = key

    # ── 2. Define what we are testing ────────────────────────
    # Pretend an agent was asked to summarise a document about
    # edge computing. Here is what it produced (actual_output),
    # and here is a reference ideal answer (expected_output).

    task_input = "Summarise the key idea of edge computing in 2 sentences."

    actual_output = (
        "Edge computing runs computations on local devices instead of "
        "sending all data to the cloud. This lowers latency and keeps "
        "sensitive data on the device, improving privacy."
    )

    expected_output = (
        "Edge computing processes data locally on devices rather than in "
        "the cloud, which reduces latency and protects privacy. However, "
        "local devices have limited compute resources."
    )

    # ── 3. Define the GEval metric ───────────────────────────
    # "criteria" tells the LLM judge what a good answer looks like.
    # The judge reads actual_output vs expected_output and scores
    # it from 0.0 to 1.0. threshold=0.5 means >=0.5 is a PASS.

    correctness_metric = GEval(
        name="Correctness",
        criteria=(
            "Determine whether the actual output correctly summarises the key "
            "idea of edge computing compared to the expected output. It should "
            "mention local/on-device processing and at least one benefit such "
            "as lower latency or improved privacy."
        ),
        evaluation_params=[
            LLMTestCaseParams.INPUT,
            LLMTestCaseParams.ACTUAL_OUTPUT,
            LLMTestCaseParams.EXPECTED_OUTPUT,
        ],
        model="gpt-4o-mini",   # the judge model (cheap)
        threshold=0.5
    )

    # ── 4. Build the test case and measure ───────────────────
    test_case = LLMTestCase(
        input=task_input,
        actual_output=actual_output,
        expected_output=expected_output
    )

    print("\nRunning GEval (this makes one LLM call to judge the output)...\n")
    correctness_metric.measure(test_case)

    # ── 5. Show the results ──────────────────────────────────
    print("-"*70)
    print(f"  Input          : {task_input}")
    print(f"  Actual Output  : {actual_output}")
    print("-"*70)
    print(f"  SCORE          : {correctness_metric.score:.3f}  (0.0 - 1.0)")
    print(f"  PASSED         : {correctness_metric.score >= correctness_metric.threshold}")
    print(f"  JUDGE'S REASON : {correctness_metric.reason}")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
