# ============================================================
# benchmark.py — Benchmark Task Definitions
# ============================================================
# All benchmark tasks live here as structured data. main.py
# loops over these instead of hardcoding tasks individually.
#
# FIELDS PER TASK:
#   id            - unique ID (e.g. "A1")
#   category      - category label
#   agent         - which agent handles it:
#                   file / code / planning / document / multimodal
#   description   - what the task asks (used in prompts + escalation)
#   input_type    - "log" | "document" | "text" | "image" | "multi" | "none"
#   input_ref     - the input:
#                     * single file path (for log/document/image)
#                     * inline string (for text/none)
#                     * a LIST of file paths (for input_type "multi")
#   scoring_mode  - how success is judged:
#                     "expected"      -> GEval against expected_output
#                     "execution"     -> run the code, pass if it works
#                     "criteria_only" -> GEval against criteria, no fixed answer
#                                        (used for ambiguous Category F tasks)
#   deeval_criteria   - GEval criteria text (None for execution mode)
#   expected_output   - reference answer (None for execution/criteria_only)
# ============================================================


TASKS = [

    # ════════════════════════════════════════════════════════
    # CATEGORY A — File and Log Analysis
    # ════════════════════════════════════════════════════════
    {
        "id": "A1",
        "category": "A - File/Log Analysis",
        "agent": "file_agent",
        "description": "Read the server log and extract all ERROR-level events with timestamps, then summarise the root cause in one sentence.",
        "input_type": "log",
        "input_ref": "tasks/sample_log.txt",
        "scoring_mode": "expected",
        "deeval_criteria": (
            "Determine whether the actual output correctly identifies the ERROR-level "
            "log lines and gives a sensible root cause summary. It should mention the "
            "cache connection failure and/or the payment processing timeout."
        ),
        "expected_output": (
            "The errors are: cache service connection failure after 3 retries, a "
            "NullPointerException in OrderService.processOrder(), and a payment "
            "processing timeout for order_id=9921. Root cause: cascading failures "
            "starting with the cache outage."
        ),
    },

    # ════════════════════════════════════════════════════════
    # CATEGORY B — Code Generation and Debugging
    # ════════════════════════════════════════════════════════
    {
        "id": "B1",
        "category": "B - Code Generation",
        "agent": "code_agent",
        "description": "Write a Python function called is_prime(n) that returns True if n is prime, else False.",
        "input_type": "none",
        "input_ref": "Write a Python function called is_prime(n) that returns True if n is prime.",
        "scoring_mode": "execution",
        "deeval_criteria": None,
        "expected_output": None,
    },

    # ════════════════════════════════════════════════════════
    # CATEGORY C — Planning and Task Decomposition
    # ════════════════════════════════════════════════════════
    {
        "id": "C1",
        "category": "C - Planning",
        "agent": "planning_agent",
        "description": "Decompose into ordered subtasks: build a data pipeline that reads CSV files, cleans the data, and outputs a summary report.",
        "input_type": "text",
        "input_ref": "Build a data pipeline that reads CSV files, cleans the data, and outputs a summary report.",
        "scoring_mode": "expected",
        "deeval_criteria": (
            "Determine whether the actual output decomposes the goal into logical, "
            "ordered subtasks covering reading CSVs, cleaning/validating data, and "
            "generating a summary report."
        ),
        "expected_output": (
            "1. Read CSV files. 2. Validate and clean the data. 3. Perform analysis. "
            "4. Generate a summary report. 5. Output the report."
        ),
    },

    # ════════════════════════════════════════════════════════
    # CATEGORY D — Document Processing
    # ════════════════════════════════════════════════════════
    {
        "id": "D1",
        "category": "D - Document Processing",
        "agent": "document_agent",
        "description": "Summarise the provided document in 2-3 sentences.",
        "input_type": "document",
        "input_ref": "tasks/sample_document.txt",
        "scoring_mode": "expected",
        "deeval_criteria": (
            "Determine whether the actual output is a faithful 2-3 sentence summary of "
            "the edge computing document, mentioning local processing and at least one "
            "benefit (privacy or latency) or challenge (limited compute)."
        ),
        "expected_output": (
            "Edge computing processes data locally rather than in the cloud, reducing "
            "latency and protecting privacy. However, local devices have limited "
            "compute resources."
        ),
    },

    # ════════════════════════════════════════════════════════
    # CATEGORY E — Multimodal
    # ════════════════════════════════════════════════════════
    {
        "id": "E1",
        "category": "E - Multimodal",
        "agent": "multimodal_agent",
        "description": "Analyse the provided screenshot and describe any errors or issues, then suggest a fix.",
        "input_type": "image",
        "input_ref": "tasks/error_screenshot.png",
        "scoring_mode": "expected",
        "deeval_criteria": (
            "Determine whether the actual output correctly identifies the error or "
            "issue in the image and suggests a plausible, specific fix."
        ),
        "expected_output": (
            "The output should name the specific error visible in the screenshot and "
            "suggest a concrete, relevant fix."
        ),
    },

    # ════════════════════════════════════════════════════════
    # CATEGORY F — Real-World Ambiguous Tasks
    # (scoring_mode: criteria_only — no single correct answer)
    # ════════════════════════════════════════════════════════
    {
        "id": "F1",
        "category": "F - Ambiguous",
        "agent": "file_agent",
        "description": "The deployment failed last night. Look at the log and figure out what happened.",
        "input_type": "log",
        "input_ref": "tasks/sample_log.txt",
        "scoring_mode": "criteria_only",
        "deeval_criteria": (
            "The request is deliberately vague. Determine whether the actual output "
            "makes a reasonable interpretation of what 'failed' means, identifies "
            "plausible issues from the log, and clearly states any assumptions it made. "
            "A good answer handles the ambiguity sensibly rather than asking for "
            "clarification or producing nothing useful."
        ),
        "expected_output": None,
    },

    # ════════════════════════════════════════════════════════
    # CATEGORY G — Complex Multi-Step Tasks
    # (input_type: multi — multiple input files)
    # ════════════════════════════════════════════════════════
    {
        "id": "G1",
        "category": "G - Complex Multi-Step",
        "agent": "file_agent",
        "description": "You are given three separate service logs. Correlate the errors across all three to identify a single shared root cause, and explain the chain of failures.",
        "input_type": "multi",
        "input_ref": [
            "tasks/service_a.log",
            "tasks/service_b.log",
            "tasks/service_c.log",
        ],
        "scoring_mode": "criteria_only",
        "deeval_criteria": (
            "Determine whether the actual output correctly correlates errors across "
            "multiple logs, identifies a plausible shared root cause, and explains the "
            "chain of failures across the services rather than treating each log in "
            "isolation."
        ),
        "expected_output": None,
    },

]